from typing import List
import re
import logging
from collections import Counter

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.schema.taxonomy import EMOTION_KEYWORDS
from data_pipeline.config import QUALITY_CONFIG


logger = logging.getLogger(__name__)


LITERARY_INDICATORS = [
    "metaphor", "simile", "imagery", "symbolism", "allusion",
    "personification", "irony", "foreshadowing",
]

DIALOGUE_INDICATORS = [
    '"', "\u201C", "\u201D", "'", "\u2018", "\u2019",
    "said", "asked", "replied", "whispered", "shouted",
]

IMAGERY_INDICATORS = [
    "like", "as if", "resembled", "appeared", "seemed",
    "looked like", "sounded like", "felt like",
]


class QualityScorer:
    def __init__(self):
        self.weights = QUALITY_CONFIG["weights"]
        self.min_score = QUALITY_CONFIG["min_quality_score"]
        self.elite_threshold = QUALITY_CONFIG["elite_threshold"]

    def score_fragments(self, fragments: List[NarrativeFragment]) -> List[NarrativeFragment]:
        scored = []
        for frag in fragments:
            score = self._calculate_quality(frag)
            frag.quality_score = score
            if score >= self.min_score:
                scored.append(frag)
        logger.info(f"Quality filter: {len(fragments)} -> {len(scored)} (min={self.min_score})")
        return scored

    def _calculate_quality(self, frag: NarrativeFragment) -> float:
        literary = self._score_literary_quality(frag.text)
        specificity = self._score_specificity(frag.text)
        emotion_clarity = self._score_emotion_clarity(frag)
        dialogue_quality = self._score_dialogue_quality(frag.text)
        imagery_quality = self._score_imagery_quality(frag.text)
        sensory_density = self._score_sensory_density(frag.text)
        uniqueness = self._score_uniqueness(frag.text)
        reusability = self._score_reusability(frag)

        total = (
            literary * self.weights["literary_quality"]
            + specificity * self.weights["specificity"]
            + emotion_clarity * self.weights["emotion_clarity"]
            + dialogue_quality * self.weights["dialogue_quality"]
            + imagery_quality * self.weights["imagery_quality"]
            + sensory_density * self.weights["sensory_density"]
            + uniqueness * self.weights["uniqueness"]
            + reusability * self.weights["reusability"]
        )

        if len(frag.text) < 20:
            total *= 0.5
        if len(frag.text) > 1500:
            total *= 0.8

        return min(1.0, max(0.0, total))

    def _score_literary_quality(self, text: str) -> float:
        text_lower = text.lower()
        score = 0.4
        literary_count = sum(1 for w in LITERARY_INDICATORS if w in text_lower)
        score += literary_count * 0.12

        sent_lengths = [len(s.split()) for s in re.split(r'[.!?]+', text) if s.strip()]
        if sent_lengths:
            avg = sum(sent_lengths) / len(sent_lengths)
            if 8 <= avg <= 35:
                score += 0.15
            elif 5 <= avg <= 45:
                score += 0.08

        vocab = set(re.findall(r'\b[a-zA-Z]{6,}\b', text_lower))
        if len(vocab) >= 12:
            score += 0.15
        elif len(vocab) >= 6:
            score += 0.08

        return min(1.0, score)

    def _score_specificity(self, text: str) -> float:
        score = 0.4
        spec_indicators = [
            r'\b\d+\b',
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',
            r'\b(?:exactly|precisely|specifically|particularly)\b',
        ]
        for pattern in spec_indicators:
            if re.search(pattern, text):
                score += 0.12

        unique_nouns = len(set(re.findall(r'\b[A-Z][a-z]+\b', text)))
        score += min(0.25, unique_nouns * 0.015)

        return min(1.0, score)

    def _score_emotion_clarity(self, frag: NarrativeFragment) -> float:
        if frag.emotion:
            if frag.emotion_intensity >= 0.6:
                return 0.85
            elif frag.emotion_intensity >= 0.3:
                return 0.65
            return 0.5
        text_lower = frag.text.lower()
        for words in EMOTION_KEYWORDS.values():
            if any(w in text_lower for w in words):
                return 0.5
        return 0.3

    def _score_dialogue_quality(self, text: str) -> float:
        score = 0.3
        dialogue_count = sum(1 for d in DIALOGUE_INDICATORS if d in text)
        if dialogue_count >= 3:
            score += 0.35
        elif dialogue_count >= 1:
            score += 0.2

        unique_speakers = len(re.findall(r'\b\w+(?=\s+said\b)', text))
        score += min(0.25, unique_speakers * 0.08)

        return min(1.0, score)

    def _score_imagery_quality(self, text: str) -> float:
        score = 0.35
        text_lower = text.lower()
        imagery_count = sum(1 for w in IMAGERY_INDICATORS if w in text_lower)
        score += imagery_count * 0.1

        color_words = {"red", "blue", "green", "black", "white", "golden",
                       "silver", "dark", "bright", "pale", "deep"}
        color_count = sum(1 for c in color_words if c in text_lower)
        score += color_count * 0.06

        if len(re.findall(r'\b\w+ly\b', text_lower)) >= 2:
            score += 0.1

        return min(1.0, score)

    def _score_sensory_density(self, text: str) -> float:
        text_lower = text.lower()
        sensory_categories = {
            "visual": ["saw", "look", "watch", "gaze", "glance", "appear", "seen", "view", "glimmer", "glow", "shadow", "light", "dark"],
            "auditory": ["heard", "sound", "voice", "whisper", "crash", "silence", "echo", "rustle", "creak", "roar", "murmur"],
            "tactile": ["felt", "touch", "warm", "cold", "soft", "hard", "texture", "smooth", "rough", "grip", "pressure"],
            "olfactory": ["smell", "scent", "aroma", "fragrance", "stench", "musty", "pungent"],
            "gustatory": ["taste", "bitter", "sweet", "sour", "salty", "delicious"],
        }

        senses_activated = 0
        for sense, words in sensory_categories.items():
            if any(w in text_lower for w in words):
                senses_activated += 1
        return min(1.0, 0.25 + senses_activated * 0.18)

    def _score_uniqueness(self, text: str) -> float:
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return 0.3
        unique_ratio = len(set(words)) / len(words)
        base = 0.35 + unique_ratio * 0.5
        return min(1.0, base)

    def _score_reusability(self, frag: NarrativeFragment) -> float:
        score = 0.35
        if frag.category:
            score += 0.15
        if frag.emotion:
            score += 0.1
        if frag.participants:
            score += 0.1
        if self._score_dialogue_quality(frag.text) > 0.4:
            score += 0.1
        if frag.tension:
            score += 0.05
        if frag.narrative_function:
            score += 0.05
        if frag.genre_hint:
            score += 0.05
        return min(1.0, score)

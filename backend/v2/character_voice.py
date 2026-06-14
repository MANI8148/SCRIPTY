"""Character Voice Fingerprint System.

Provides deterministic voice fingerprints from CharacterRecord traits,
enabling distinct dialogue generation per character.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.v2.types import CharacterRecord, Intention, RelationKind


# ---------------------------------------------------------------------------
# VoiceFingerprint — complete description of how a character speaks
# ---------------------------------------------------------------------------


@dataclass
class VoiceFingerprint:
    """Deterministically derived voice profile for a character.

    All fields are computed from CharacterRecord traits, role, and
    emotional baseline — never set manually.
    """

    character_name: str
    traits: list[str] = field(default_factory=list)
    speech_rhythm: str = "moderate"  # terse / moderate / verbose / poetic
    vocabulary_level: str = "moderate"  # simple / moderate / sophisticated / archaic
    signature_phrases: list[str] = field(default_factory=list)
    sentence_tendency: str = "varied"  # short / varied / complex / fragmented
    dialogue_habits: list[str] = field(default_factory=list)
    emotional_leakage: str = "direct"  # direct / subtle / repressed / explosive / calculated
    formality: float = 0.5  # 0 = crude, 1 = formal


# ---------------------------------------------------------------------------
# VoiceFingerprintBuilder — builds fingerprints from CharacterRecord
# ---------------------------------------------------------------------------


class VoiceFingerprintBuilder:
    """Constructs VoiceFingerprint instances from character records."""

    # Trait → speech rhythm mappings
    _RHYTHM_MAP: dict[str, str] = {
        "pious": "poetic",
        "spiritual": "poetic",
        "thoughtful": "moderate",
        "wise": "moderate",
        "learned": "verbose",
        "patient": "moderate",
        "rude": "terse",
        "brash": "terse",
        "reckless": "terse",
        "kind": "moderate",
        "gentle": "moderate",
        "compassionate": "moderate",
        "deceptive": "moderate",
        "cunning": "moderate",
        "sly": "moderate",
        "proud": "verbose",
        "ambitious": "verbose",
        "arrogant": "verbose",
        "curious": "moderate",
        "brave": "terse",
        "cautious": "moderate",
        "loyal": "moderate",
        "angry": "terse",
        "bitter": "terse",
        "hopeful": "moderate",
        "melancholic": "poetic",
        "mysterious": "moderate",
        "charismatic": "verbose",
    }

    # Trait → vocabulary level
    _VOCAB_MAP: dict[str, str] = {
        "pious": "archaic",
        "spiritual": "archaic",
        "wise": "sophisticated",
        "learned": "sophisticated",
        "rude": "simple",
        "brash": "simple",
        "kind": "moderate",
        "deceptive": "sophisticated",
        "cunning": "sophisticated",
        "proud": "sophisticated",
        "arrogant": "moderate",
        "patient": "moderate",
        "curious": "moderate",
        "brave": "simple",
        "cautious": "moderate",
        "melancholic": "sophisticated",
        "mysterious": "moderate",
        "charismatic": "sophisticated",
        "gentle": "moderate",
        "compassionate": "moderate",
        "loyal": "simple",
        "ambitious": "sophisticated",
        "hopeful": "moderate",
        "angry": "simple",
        "bitter": "moderate",
    }

    # Trait → emotional leakage
    _LEAKAGE_MAP: dict[str, str] = {
        "pious": "repressed",
        "spiritual": "repressed",
        "wise": "calculated",
        "learned": "calculated",
        "patient": "subtle",
        "rude": "explosive",
        "brash": "explosive",
        "reckless": "explosive",
        "kind": "subtle",
        "gentle": "subtle",
        "compassionate": "subtle",
        "deceptive": "calculated",
        "cunning": "calculated",
        "sly": "calculated",
        "proud": "direct",
        "ambitious": "direct",
        "arrogant": "direct",
        "curious": "direct",
        "brave": "direct",
        "cautious": "repressed",
        "loyal": "direct",
        "angry": "explosive",
        "bitter": "explosive",
        "hopeful": "direct",
        "melancholic": "subtle",
        "mysterious": "repressed",
        "charismatic": "calculated",
    }

    # Trait → sentence tendency
    _SENTENCE_MAP: dict[str, str] = {
        "pious": "complex",
        "spiritual": "complex",
        "wise": "complex",
        "learned": "complex",
        "patient": "varied",
        "rude": "short",
        "brash": "short",
        "reckless": "short",
        "kind": "varied",
        "gentle": "varied",
        "compassionate": "varied",
        "deceptive": "complex",
        "cunning": "complex",
        "sly": "complex",
        "proud": "complex",
        "ambitious": "varied",
        "arrogant": "short",
        "curious": "varied",
        "brave": "short",
        "cautious": "varied",
        "loyal": "short",
        "angry": "fragmented",
        "bitter": "fragmented",
        "hopeful": "varied",
        "melancholic": "complex",
        "mysterious": "fragmented",
        "charismatic": "varied",
    }

    # Primary trait → dialogue habits (each trait contributes 1-2 habits)
    _HABITS_MAP: dict[str, list[str]] = {
        "pious": ["references divine will", "speaks in blessings or prayers"],
        "spiritual": ["speaks of fate and destiny", "uses ritual phrases"],
        "wise": ["uses proverbs", "pauses thoughtfully before speaking"],
        "learned": ["cites obscure references", "corrects others' terminology"],
        "patient": ["lets others finish speaking", "repeats for clarity"],
        "rude": ["interrupts others", "uses dismissive language"],
        "brash": ["speaks without thinking", "cuts others off mid-sentence"],
        "reckless": ["blurts out secrets", "speaks too loudly"],
        "kind": ["apologizes frequently", "uses gentle encouragement"],
        "gentle": ["speaks softly", "uses soothing phrases"],
        "compassionate": ["asks about others' wellbeing", "offers reassurance"],
        "deceptive": ["speaks in riddles", "avoids direct answers"],
        "cunning": ["uses half-truths", "changes subject abruptly"],
        "sly": ["uses flattery", "speaks in double meanings"],
        "proud": ["uses declarative I-statements", "dismisses others' opinions"],
        "ambitious": ["talks about future plans", "uses strategic language"],
        "arrogant": ["belittles others", "boasts about achievements"],
        "curious": ["asks many questions", "follows tangents"],
        "brave": ["speaks directly", "uses short commands"],
        "cautious": ["hedges statements", "asks for confirmation"],
        "loyal": ["uses we-statements", "defends others"],
        "angry": ["uses short outbursts", "repeats for emphasis"],
        "bitter": ["uses sarcasm", "makes cutting remarks"],
        "hopeful": ["uses optimistic language", "encourages others"],
        "melancholic": ["trails off mid-sentence", "uses mournful phrases"],
        "mysterious": ["speaks in fragments", "leaves sentences unfinished"],
        "charismatic": ["uses rhetorical questions", "addresses listeners directly"],
    }

    # Role → signature phrases
    _ROLE_PHRASES: dict[str, list[str]] = {
        "protagonist": [
            "I have to do this.",
            "There is no other way.",
            "I will see this through.",
        ],
        "antagonist": [
            "You cannot stop me.",
            "This is only the beginning.",
            "You have no idea what is coming.",
        ],
        "mentor": [
            "Listen carefully.",
            "I have seen this before.",
            "You are not ready yet.",
        ],
        "sidekick": [
            "Are you sure about this?",
            "I have got your back.",
            "What is the plan?",
        ],
        "sage": [
            "The answer lies within.",
            "Patience, young one.",
            "All will be revealed in time.",
        ],
        "trickster": [
            "Would not you like to know?",
            "Trust me — or do not.",
            "Things are not what they seem.",
        ],
        "leader": [
            "We move together.",
            "Trust my judgment.",
            "This is not up for debate.",
        ],
        "bystander": [
            "I do not want any trouble.",
            "Leave me out of this.",
            "I did not see anything.",
        ],
        "villain": [
            "How amusing.",
            "You think you can challenge me?",
            "Fools. All of you.",
        ],
        "hero": [
            "I will protect everyone.",
            "No one else gets hurt.",
            "Stand behind me.",
        ],
    }

    _FALLBACK_PHRASES: list[str] = [
        "I think so.",
        "Maybe.",
        "Let me think about that.",
    ]

    def build(self, character: CharacterRecord) -> VoiceFingerprint:
        """Build a complete VoiceFingerprint from a CharacterRecord."""
        traits_lower = [t.lower() for t in character.traits]
        primary_trait = traits_lower[0] if traits_lower else "curious"

        rhythm = self._pick_by_priority(traits_lower, self._RHYTHM_MAP, "moderate")
        vocab = self._pick_by_priority(traits_lower, self._VOCAB_MAP, "moderate")
        leakage = self._pick_by_priority(traits_lower, self._LEAKAGE_MAP, "direct")
        sentence = self._pick_by_priority(traits_lower, self._SENTENCE_MAP, "varied")

        habits: list[str] = []
        for t in traits_lower:
            if t in self._HABITS_MAP:
                for h in self._HABITS_MAP[t]:
                    if h not in habits:
                        habits.append(h)
        if not habits:
            habits = ["speaks plainly"]

        phrases = list(self._ROLE_PHRASES.get(character.role, self._FALLBACK_PHRASES))

        formality = self._compute_formality(traits_lower, character.role)

        return VoiceFingerprint(
            character_name=character.name,
            traits=character.traits[:],
            speech_rhythm=rhythm,
            vocabulary_level=vocab,
            signature_phrases=phrases,
            sentence_tendency=sentence,
            dialogue_habits=habits,
            emotional_leakage=leakage,
            formality=formality,
        )

    def get_dialogue_style(
        self,
        fingerprint: VoiceFingerprint,
        intention: Intention | None = None,
        emotional_state: str = "neutral",
    ) -> dict[str, Any]:
        """Return style modifiers for dialogue generation."""
        # Sentence length target
        tendency = fingerprint.sentence_tendency
        if tendency in ("short", "fragmented"):
            sentence_length = "short"
        elif tendency == "complex":
            sentence_length = "long"
        elif tendency == "varied":
            sentence_length = "medium"
        else:
            sentence_length = "medium"

        # Contracted vs formal speech
        use_contractions = fingerprint.formality < 0.5
        use_formality = fingerprint.formality > 0.7

        # Interruption likelihood
        interruption_likelihood = 0.0
        if "interrupts others" in fingerprint.dialogue_habits:
            interruption_likelihood += 0.4
        if "cuts others off mid-sentence" in fingerprint.dialogue_habits:
            interruption_likelihood += 0.3
        interruption_likelihood = min(1.0, interruption_likelihood + 0.1)

        # Rhetorical questions
        rhetorical_questions = "asks rhetorical questions" in fingerprint.dialogue_habits or "uses rhetorical questions" in fingerprint.dialogue_habits

        # Emphasis pattern
        emphasis = "none"
        if "repeats for emphasis" in fingerprint.dialogue_habits:
            emphasis = "repetition"
        elif "uses short outbursts" in fingerprint.dialogue_habits:
            emphasis = "intensity"
        elif "speaks too loudly" in fingerprint.dialogue_habits:
            emphasis = "volume"
        elif "uses sarcasm" in fingerprint.dialogue_habits:
            emphasis = "sarcasm"

        return {
            "sentence_length_target": sentence_length,
            "use_contractions": use_contractions,
            "use_formality": use_formality,
            "interruption_likelihood": interruption_likelihood,
            "rhetorical_questions": rhetorical_questions,
            "emphasis_pattern": emphasis,
        }

    def _pick_by_priority(
        self,
        traits: list[str],
        mapping: dict[str, str],
        default: str,
    ) -> str:
        """Pick the mapping value for the highest-priority trait that exists."""
        for trait in traits:
            if trait in mapping:
                return mapping[trait]
        return default

    def _compute_formality(
        self, traits: list[str], role: str
    ) -> float:
        """Compute formality score from 0 (crude) to 1 (formal)."""
        score = 0.5  # baseline

        formality_shifts: dict[str, float] = {
            "pious": +0.3,
            "spiritual": +0.2,
            "wise": +0.3,
            "learned": +0.3,
            "rude": -0.3,
            "brash": -0.3,
            "reckless": -0.2,
            "kind": +0.1,
            "gentle": +0.1,
            "deceptive": +0.1,
            "cunning": +0.2,
            "sly": +0.0,
            "proud": +0.2,
            "ambitious": +0.2,
            "arrogant": -0.1,
            "curious": 0.0,
            "brave": -0.1,
            "cautious": +0.1,
            "loyal": 0.0,
            "angry": -0.2,
            "bitter": -0.1,
            "hopeful": 0.0,
            "melancholic": +0.2,
            "mysterious": 0.0,
            "charismatic": +0.2,
        }

        role_shifts: dict[str, float] = {
            "sage": +0.2,
            "mentor": +0.15,
            "leader": +0.15,
            "villain": -0.1,
            "trickster": -0.1,
            "bystander": 0.0,
        }

        for trait in traits:
            score += formality_shifts.get(trait, 0.0)
        score += role_shifts.get(role, 0.0)

        return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def voice_distinctiveness(
    fingerprints: list[VoiceFingerprint],
) -> float:
    """Measure how distinct voices are from each other.

    Returns 0.0 if all voices are identical, 1.0 if fully distinct.
    """
    if len(fingerprints) < 2:
        return 1.0

    comparisons = 0
    total_distance = 0.0

    for i in range(len(fingerprints)):
        for j in range(i + 1, len(fingerprints)):
            a = fingerprints[i]
            b = fingerprints[j]
            total_distance += _fingerprint_distance(a, b)
            comparisons += 1

    if comparisons == 0:
        return 1.0
    return total_distance / comparisons


def _fingerprint_distance(a: VoiceFingerprint, b: VoiceFingerprint) -> float:
    """Compute distance between two fingerprints on [0, 1]."""
    distances: list[float] = []

    # Speech rhythm
    rhythm_values = {"terse": 0.0, "moderate": 0.33, "verbose": 0.66, "poetic": 1.0}
    ar = rhythm_values.get(a.speech_rhythm, 0.5)
    br = rhythm_values.get(b.speech_rhythm, 0.5)
    distances.append(abs(ar - br))

    # Vocabulary level
    vocab_values = {"simple": 0.0, "moderate": 0.33, "sophisticated": 0.66, "archaic": 1.0}
    av = vocab_values.get(a.vocabulary_level, 0.5)
    bv = vocab_values.get(b.vocabulary_level, 0.5)
    distances.append(abs(av - bv))

    # Sentence tendency
    sent_values = {"short": 0.0, "varied": 0.33, "complex": 0.66, "fragmented": 1.0}
    as_ = sent_values.get(a.sentence_tendency, 0.5)
    bs = sent_values.get(b.sentence_tendency, 0.5)
    distances.append(abs(as_ - bs))

    # Emotional leakage
    leak_values = {"repressed": 0.0, "subtle": 0.25, "calculated": 0.5, "direct": 0.75, "explosive": 1.0}
    al = leak_values.get(a.emotional_leakage, 0.5)
    bl = leak_values.get(b.emotional_leakage, 0.5)
    distances.append(abs(al - bl))

    # Formality difference
    distances.append(abs(a.formality - b.formality))

    # Signature phrase overlap (Jaccard-like)
    phrases_a = set(p.lower() for p in a.signature_phrases)
    phrases_b = set(p.lower() for p in b.signature_phrases)
    if phrases_a or phrases_b:
        intersection = len(phrases_a & phrases_b)
        union = len(phrases_a | phrases_b)
        phrase_similarity = intersection / max(union, 1)
        distances.append(1.0 - phrase_similarity)
    else:
        distances.append(0.5)

    # Dialogue habit overlap
    habits_a = set(h.lower() for h in a.dialogue_habits)
    habits_b = set(h.lower() for h in b.dialogue_habits)
    if habits_a or habits_b:
        h_intersection = len(habits_a & habits_b)
        h_union = len(habits_a | habits_b)
        habit_similarity = h_intersection / max(h_union, 1)
        distances.append(1.0 - habit_similarity)
    else:
        distances.append(0.5)

    return sum(distances) / max(len(distances), 1)


def voice_report(fingerprints: list[VoiceFingerprint]) -> str:
    """Produce a human-readable fingerprint summary."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("CHARACTER VOICE FINGERPRINT REPORT")
    lines.append("=" * 60)
    lines.append("")

    for fp in fingerprints:
        lines.append(f"--- {fp.character_name} ---")
        lines.append(f"  Traits:             {', '.join(fp.traits)}")
        lines.append(f"  Speech Rhythm:      {fp.speech_rhythm}")
        lines.append(f"  Vocabulary Level:   {fp.vocabulary_level}")
        lines.append(f"  Sentence Tendency:  {fp.sentence_tendency}")
        lines.append(f"  Emotional Leakage:  {fp.emotional_leakage}")
        lines.append(f"  Formality:          {fp.formality:.2f}")
        lines.append(f"  Signature Phrases:  {' | '.join(fp.signature_phrases[:3])}")
        lines.append(f"  Dialogue Habits:    {' | '.join(fp.dialogue_habits[:3])}")
        lines.append("")

    if len(fingerprints) >= 2:
        distinct = voice_distinctiveness(fingerprints)
        lines.append("-" * 40)
        lines.append(f"Overall Voice Distinctiveness: {distinct:.3f}")
        if distinct > 0.7:
            lines.append("  ✓ Highly distinctive cast")
        elif distinct > 0.4:
            lines.append("  ~ Moderately distinctive")
        else:
            lines.append("  ✗ Characters sound too similar")
        lines.append("")

    return "\n".join(lines)

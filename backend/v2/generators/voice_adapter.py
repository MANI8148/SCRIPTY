"""
SCRIPTY v2 — VoiceAdapter
Modulates token probability distributions by character OCEAN personality traits.
High openness -> broader vocabulary
High extraversion -> more active verbs
Default modulation strength: 10% (configurable)
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from backend.v2.types import CharacterRecord


@dataclass
class VoiceFingerprint:
    """Deterministic voice profile derived from OCEAN traits."""
    formality: float = 0.5
    vocabulary_complexity: float = 0.5
    verbosity: float = 0.5
    emotional_expressiveness: float = 0.5
    directness: float = 0.5
    active_verb_preference: float = 0.5
    sentence_length_pref: float = 0.5

    @classmethod
    def from_ocean(cls, ocean: dict[str, float]) -> "VoiceFingerprint":
        openness = ocean.get("openness", 0.5)
        conscientiousness = ocean.get("conscientiousness", 0.5)
        extraversion = ocean.get("extraversion", 0.5)
        agreeableness = ocean.get("agreeableness", 0.5)
        neuroticism = ocean.get("neuroticism", 0.5)

        return cls(
            formality=0.3 + 0.4 * conscientiousness,
            vocabulary_complexity=0.3 + 0.5 * openness,
            verbosity=0.3 + 0.4 * extraversion,
            emotional_expressiveness=0.2 + 0.6 * (1 - neuroticism),
            directness=0.3 + 0.4 * (1 - agreeableness),
            active_verb_preference=0.3 + 0.5 * extraversion,
            sentence_length_pref=0.3 + 0.4 * openness,
        )


class VoiceAdapter:
    """
    Modulates token probability distributions by character voice fingerprint.
    Applied during token-by-token generation in HybridGenerator.
    """

    MODULATION_STRENGTH = 0.10  # 10% default

    def __init__(self, modulation_strength: float = 0.10):
        self.modulation_strength = modulation_strength
        self._active_verbs = {
            "grabbed", "sprinted", "shouted", "demanded", "seized", "charged",
            "confronted", "pursued", "attacked", "defended", "raced", "lunged"
        }
        self._passive_verbs = {
            "was", "were", "had", "felt", "seemed", "appeared", "became",
            "remained", "stayed", "waited", "watched", "observed", "listened"
        }
        self._complex_words = {
            "nevertheless", "furthermore", "consequently", "subsequently",
            "nevertheless", "moreover", "accordingly", "simultaneously"
        }

    def modulate(self, prob_dist: dict[str, float], fingerprint: VoiceFingerprint) -> dict[str, float]:
        """Apply voice modulation to probability distribution."""
        if not prob_dist:
            return prob_dist

        modulated = dict(prob_dist)
        vocab = list(modulated.keys())

        for token in vocab:
            base_prob = modulated[token]
            multiplier = 1.0

            token_lower = token.lower()

            if fingerprint.active_verb_preference > 0.6 and token_lower in self._active_verbs:
                multiplier += self.modulation_strength * fingerprint.active_verb_preference
            elif fingerprint.active_verb_preference < 0.4 and token_lower in self._passive_verbs:
                multiplier += self.modulation_strength * (1 - fingerprint.active_verb_preference)

            if fingerprint.vocabulary_complexity > 0.6 and token_lower in self._complex_words:
                multiplier += self.modulation_strength * fingerprint.vocabulary_complexity

            if fingerprint.formality > 0.6 and token_lower in {"gonna", "wanna", "gotta", "yeah", "nah"}:
                multiplier *= 0.5
            elif fingerprint.formality < 0.4 and token_lower in {"however", "therefore", "furthermore"}:
                multiplier *= 0.7

            modulated[token] = base_prob * multiplier

        total = sum(modulated.values())
        if total > 0:
            modulated = {k: v / total for k, v in modulated.items()}

        return modulated

    def adapt_sentence(self, sentence: str, fingerprint: VoiceFingerprint) -> str:
        """Post-generation adaptation of sentence structure."""
        words = sentence.split()

        if fingerprint.verbosity > 0.7 and len(words) < 10:
            pass

        if fingerprint.directness > 0.7:
            sentence = sentence.replace("it seems that ", "").replace("it appears that ", "")

        return sentence


class VoiceAdapterPool:
    """Manages voice fingerprints for multiple characters."""

    def __init__(self):
        self._fingerprints: dict[str, VoiceFingerprint] = {}

    def register(self, character: CharacterRecord) -> VoiceFingerprint:
        ocean = character.ocean or {}
        fp = VoiceFingerprint.from_ocean(ocean)
        self._fingerprints[character.name] = fp
        return fp

    def get(self, character_name: str) -> Optional[VoiceFingerprint]:
        return self._fingerprints.get(character_name)

    def get_or_create(self, character: CharacterRecord) -> VoiceFingerprint:
        if character.name not in self._fingerprints:
            return self.register(character)
        return self._fingerprints[character.name]
"""Modulates token probability distributions by character OCEAN traits.

Provides deterministic probability adjustments so that characters
with different personalities produce measurably different text.
"""

from __future__ import annotations

from typing import Any


class VoiceAdapter:
    """Modulates token probabilities based on character voice fingerprints.

    Maps VoiceFingerprint fields (vocabulary_level, speech_rhythm,
    sentence_tendency, formality, emotional_leakage) to token-level
    probability adjustments.

    Modulation strength defaults to 10% and is configurable.
    """

    def __init__(self, modulation_strength: float = 0.1) -> None:
        self.strength = modulation_strength

    def modulate_distribution(
        self,
        tokens: list[str],
        probabilities: list[float],
        voice_fingerprint: dict[str, Any],
    ) -> list[float]:
        """Adjust token probabilities according to character voice.

        Args:
            tokens: Candidate tokens to choose from.
            probabilities: Corresponding base probabilities.
            voice_fingerprint: Dict from CharacterAgent.voice_fingerprint().

        Returns:
            Adjusted probability distribution (same length, sums to 1).
        """
        if not tokens or not probabilities:
            return probabilities

        probs = list(probabilities)
        vocab = voice_fingerprint.get("vocabulary_level", "moderate")
        formality = voice_fingerprint.get("formality", 0.5)

        for i, token in enumerate(tokens):
            if vocab == "sophisticated" or vocab == "archaic":
                if self._is_sophisticated(token):
                    probs[i] *= 1.0 + self.strength
                if self._is_simple(token):
                    probs[i] *= 1.0 - self.strength * 0.5
            elif vocab == "simple":
                if self._is_simple(token):
                    probs[i] *= 1.0 + self.strength
                if self._is_sophisticated(token):
                    probs[i] *= 1.0 - self.strength

            if formality > 0.7:
                if self._is_formal(token):
                    probs[i] *= 1.0 + self.strength
                if self._is_informal(token):
                    probs[i] *= 1.0 - self.strength
            elif formality < 0.3:
                if self._is_informal(token):
                    probs[i] *= 1.0 + self.strength
                if self._is_formal(token):
                    probs[i] *= 1.0 - self.strength

            if self._is_active_verb(token):
                extraversion = voice_fingerprint.get("extraversion", 0.5)
                if extraversion > 0.6:
                    probs[i] *= 1.0 + self.strength * 0.5
                elif extraversion < 0.4:
                    probs[i] *= 1.0 - self.strength * 0.5

        total = sum(probs)
        if total > 0:
            probs = [p / total for p in probs]
        return probs

    def _is_sophisticated(self, token: str) -> bool:
        token_lower = token.lower()
        return token_lower in {
            "therefore", "nevertheless", "consequently", "accordingly",
            "furthermore", "moreover", "notwithstanding", "wherein",
            "whereby", "hitherto", "thenceforth", "thereupon",
            "melancholy", "magnificent", "extraordinary", "remarkable",
            "contemplated", "endeavored", "perceive", "comprehend",
            "benevolent", "malevolent", "predestined", "ineffable",
        }

    def _is_simple(self, token: str) -> bool:
        token_lower = token.lower()
        return token_lower in {
            "good", "bad", "big", "small", "nice", "mean",
            "go", "get", "do", "say", "make", "take", "come",
            "see", "know", "got", "went", "thing", "stuff",
            "yeah", "nope", "okay", "fine", "sure", "well",
        }

    def _is_formal(self, token: str) -> bool:
        token_lower = token.lower()
        return token_lower in {
            "shall", "ought", "must", "indeed", "quite",
            "sir", "madam", "pardon", "apologies",
            "request", "require", "instruct", "direct",
        }

    def _is_informal(self, token: str) -> bool:
        token_lower = token.lower()
        return token_lower in {
            "gonna", "wanna", "gotta", "ain't", "y'all",
            "yeah", "nah", "c'mon", "dunno", "kinda",
            "sorta", "lot", "guy", "dude", "pal",
        }

    def _is_active_verb(self, token: str) -> bool:
        token_lower = token.lower()
        return token_lower in {
            "ran", "fought", "charged", "struck", "grabbed",
            "pushed", "pulled", "threw", "kicked", "hit",
            "dashed", "sprinted", "leaped", "seized", "smashed",
            "attacked", "advanced", "lunged", "rushed", "broke",
        }

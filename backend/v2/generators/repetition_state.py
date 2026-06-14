"""Token-level repetition tracking across scenes.

Prevents the generator from repeating the same phrases, dialogue lines,
body language descriptions, and sentence openings within a configurable
window.
"""

from __future__ import annotations

import re

from collections import deque


class RepetitionState:
    """Tracks recently used tokens across narrative categories.

    Each category maintains a sliding window of recent tokens.
    `is_repeated()` returns True if a new token would duplicate
    content within the window.

    Categories: dialogue, body_language, emotion, action, opening
    """

    def __init__(self, window: int = 100) -> None:
        self.window = window
        self._history: dict[str, deque[str]] = {
            "dialogue": deque(maxlen=window),
            "body_language": deque(maxlen=window),
            "emotion": deque(maxlen=window),
            "action": deque(maxlen=window),
            "opening": deque(maxlen=window),
        }

    def is_repeated(self, text: str, category: str = "dialogue") -> bool:
        """Check if text (or significant substring) appears in category history."""
        normalized = self._normalize(text)
        if len(normalized) < 5:
            return False

        history = self._history.get(category)
        if history is None:
            return False

        for entry in history:
            if self._overlap_ratio(normalized, entry) > 0.7:
                return True
        return False

    def track(self, text: str, category: str = "dialogue") -> None:
        """Add text to the category history."""
        history = self._history.get(category)
        if history is None:
            return
        history.append(self._normalize(text))

    def fresh_dialogue(self, text: str) -> bool:
        """Check dialogue line freshness."""
        return not self.is_repeated(text, "dialogue")

    def fresh_body_language(self, text: str) -> bool:
        """Check body language freshness."""
        return not self.is_repeated(text, "body_language")

    def fresh_opening(self, text: str) -> bool:
        """Check sentence/phrase opening freshness."""
        return not self.is_repeated(text, "opening")

    def clear(self) -> None:
        for d in self._history.values():
            d.clear()

    def stats(self) -> dict[str, int]:
        return {k: len(v) for k, v in self._history.items()}

    def _normalize(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        return text

    def _overlap_ratio(self, a: str, b: str) -> float:
        """Compute bigram overlap ratio between two strings."""
        a_bigrams = set(self._bigrams(a))
        b_bigrams = set(self._bigrams(b))
        if not a_bigrams or not b_bigrams:
            return 0.0
        intersection = a_bigrams & b_bigrams
        return len(intersection) / max(len(a_bigrams), len(b_bigrams))

    @staticmethod
    def _bigrams(text: str) -> list[str]:
        words = text.split()
        return [" ".join(words[i : i + 2]) for i in range(len(words) - 1)]

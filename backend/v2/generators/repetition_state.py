"""
SCRIPTY v2 — RepetitionState
Token-level dedup across scenes.
Tracks: dialogue lines, body-language phrases, sentence starts, scene openings.
Window-based tracking (configurable, default 100 tokens).
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RepetitionState:
    """
    Tracks repetitions across multiple categories with sliding windows.
    Used by HybridGenerator to avoid repetitive prose.
    """
    window_size: int = 100

    dialogue_lines: deque[str] = field(default_factory=lambda: deque(maxlen=100))
    body_language: deque[str] = field(default_factory=lambda: deque(maxlen=100))
    sentence_starts: deque[str] = field(default_factory=lambda: deque(maxlen=100))
    scene_openings: deque[str] = field(default_factory=lambda: deque(maxlen=20))

    _token_buffer: deque[str] = field(default_factory=lambda: deque(maxlen=100))

    def track(self, tokens: list[str], category: str = "general") -> None:
        """Add tokens to tracking buffers.

        Accepts either a token list or a raw string (for callers that pass
        pre-joined text). Internally normalised to a token list.
        """
        if isinstance(tokens, str):
            tokens = tokens.split()
        self._token_buffer.extend(tokens)

        text = " ".join(tokens).strip()

        if category == "dialogue" or ("\"" in text or '"' in text):
            self.dialogue_lines.append(text[:200])

        body_patterns = ["nodded", "smiled", "frowned", "shook", "gestured", "turned", "looked", "glanced"]
        if any(p in text.lower() for p in body_patterns):
            self.body_language.append(text[:200])

        if tokens:
            start = " ".join(tokens[:3])
            self.sentence_starts.append(start)

    # Alias kept for backwards-compatible callers (tests, generators).
    def is_repeated(self, tokens: list[str], category: str = "general") -> bool:
        if isinstance(tokens, str):
            tokens = tokens.split()
        return self.is_repetitive(tokens, category)

    def is_repetitive(self, tokens: list[str], category: str = "general", threshold: float = 0.7) -> bool:
        """Check if tokens would be repetitive."""
        if not tokens:
            return False

        text = " ".join(tokens).strip()
        start = " ".join(tokens[:3])

        if category == "dialogue" or ("\"" in text or '"' in text):
            for existing in self.dialogue_lines:
                if self._similarity(text, existing) > threshold:
                    return True

        if any(p in text.lower() for p in ["nodded", "smiled", "frowned", "shook", "gestured", "turned", "looked", "glanced"]):
            for existing in self.body_language:
                if self._similarity(text, existing) > threshold:
                    return True

        for existing in self.sentence_starts:
            if self._similarity(start, existing) > threshold:
                return True

        return False

    def _similarity(self, a: str, b: str) -> float:
        """Simple word-overlap similarity."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def get_recent_starts(self, n: int = 5) -> list[str]:
        """Get recent sentence starts for variation checking."""
        return list(self.sentence_starts)[-n:]

    def clear_category(self, category: str) -> None:
        """Clear a specific tracking category."""
        if category == "dialogue":
            self.dialogue_lines.clear()
        elif category == "body_language":
            self.body_language.clear()
        elif category == "sentence_starts":
            self.sentence_starts.clear()
        elif category == "scene_openings":
            self.scene_openings.clear()

    def reset(self) -> None:
        """Reset all tracking."""
        self.dialogue_lines.clear()
        self.body_language.clear()
        self.sentence_starts.clear()
        self.scene_openings.clear()
        self._token_buffer.clear()
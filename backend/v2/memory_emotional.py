"""
SCRIPTY v2 — EmotionalRetrieval
Emotion-based memory recall (lazy-loaded).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.v2.types import MemoryEntry


@dataclass
class EmotionalRetrieval:
    emotional_index: dict[str, list[MemoryEntry]] = field(default_factory=dict)

    def process(self, character: str, entry: MemoryEntry):
        emotion_key = self._dominant_emotion(entry)
        if emotion_key not in self.emotional_index:
            self.emotional_index[emotion_key] = []
        self.emotional_index[emotion_key].append(entry)

    def _dominant_emotion(self, entry: MemoryEntry) -> str:
        if entry.emotional_impact > 0.7:
            return "high"
        elif entry.emotional_impact > 0.3:
            return "medium"
        return "low"

    def retrieve(self, character: str, blueprint) -> list[MemoryEntry]:
        return self.emotional_index.get("high", [])[-3:] + self.emotional_index.get("medium", [])[-2:]
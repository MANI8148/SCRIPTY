"""
SCRIPTY v2 — InterpretationMemory
Character-specific event interpretation (lazy-loaded).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.v2.types import MemoryEntry


@dataclass
class InterpretationMemory:
    interpretations: dict[str, list[MemoryEntry]] = field(default_factory=dict)

    def process(self, character: str, entry: MemoryEntry):
        if character not in self.interpretations:
            self.interpretations[character] = []
        interp = MemoryEntry(
            character=character,
            content=f"Interpreted: {entry.content}",
            scene_num=entry.scene_num,
            chapter_num=entry.chapter_num,
            event_type="interpretation",
            emotional_impact=entry.emotional_impact * 0.8,
            importance=entry.importance * 0.9,
            metadata={"original_event": entry.content[:100]}
        )
        self.interpretations[character].append(interp)

    def retrieve(self, character: str, blueprint) -> list[MemoryEntry]:
        return self.interpretations.get(character, [])[-5:]
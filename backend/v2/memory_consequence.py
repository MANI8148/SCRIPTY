"""
SCRIPTY v2 — ConsequenceMemory
Action outcome tracking (lazy-loaded).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.v2.types import MemoryEntry


@dataclass
class ConsequenceMemory:
    consequences: dict[str, list[MemoryEntry]] = field(default_factory=dict)

    def process(self, character: str, entry: MemoryEntry):
        if character not in self.consequences:
            self.consequences[character] = []
        conseq = MemoryEntry(
            character=character,
            content=f"Consequence of: {entry.content}",
            scene_num=entry.scene_num,
            chapter_num=entry.chapter_num,
            event_type="consequence",
            emotional_impact=entry.emotional_impact * 0.7,
            importance=entry.importance * 0.8,
            metadata={"original_event": entry.content[:100]}
        )
        self.consequences[character].append(conseq)

    def retrieve(self, character: str, blueprint) -> list[MemoryEntry]:
        return self.consequences.get(character, [])[-5:]
"""
SCRIPTY v2 — RelationshipDelta
Relationship change history (lazy-loaded).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.v2.types import MemoryEntry


@dataclass
class RelationshipDelta:
    deltas: dict[str, list[MemoryEntry]] = field(default_factory=dict)

    # Relation kind -> sentiment polarity. Used by MemorySystem
    # current_relationship_sentiment() to derive a float from stored deltas.
    _RELATION_SENTIMENT: dict[str, float] = field(
        default_factory=lambda: {
            "enemy": -1.0,
            "rival": -0.5,
            "neutral": 0.0,
            "subordinate": 0.1,
            "ally": 0.5,
            "mentor": 0.6,
            "family": 0.7,
        }
    )

    def process(self, character: str, entry: MemoryEntry, relation: Any = None):
        if character not in self.deltas:
            self.deltas[character] = []
        delta = MemoryEntry(
            character=character,
            content=f"Relationship shift: {entry.content}",
            scene_num=entry.scene_num,
            chapter_num=entry.chapter_num,
            event_type="relationship_delta",
            emotional_impact=entry.emotional_impact,
            importance=entry.importance * 0.9,
            metadata={"original_event": entry.content[:100], "relation": relation}
        )
        self.deltas[character].append(delta)

    def retrieve(self, character: str, blueprint) -> list[MemoryEntry]:
        return self.deltas.get(character, [])[-3:]

    def sentiment(self, a: str, b: str) -> float:
        """Derive relationship sentiment for the (a, b) pair.

        Scans stored deltas for either character whose content mentions
        the other, and returns the polarity of the most recent relation
        recorded between them. Returns 0.0 when no relation is known.
        """
        best_rel = None
        for ch in (a, b):
            for entry in self.deltas.get(ch, []):
                content = (entry.content or "").lower()
                if b.lower() in content or a.lower() in content:
                    rel = (entry.metadata or {}).get("relation")
                    if rel is not None:
                        best_rel = rel
        if best_rel is None:
            return 0.0
        return self._RELATION_SENTIMENT.get(str(best_rel).lower(), 0.0)
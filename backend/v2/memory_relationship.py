"""Relationship Delta Tracker — log and analyze relationship changes.

Every relationship change is tracked as a first-class event that directly
affects character deliberation, emotional pressure, and scene outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.v2.types import RelationKind, RelationshipDelta


# Sentiment weights for each relation type
_RELATION_SENTIMENT: dict[RelationKind, float] = {
    RelationKind.ALLY: 0.8,
    RelationKind.FAMILY: 0.9,
    RelationKind.MENTOR: 0.6,
    RelationKind.NEUTRAL: 0.0,
    RelationKind.SUBORDINATE: 0.2,
    RelationKind.RIVAL: -0.5,
    RelationKind.ENEMY: -0.9,
}


@dataclass
class RelationshipDeltaStore:
    deltas: list[RelationshipDelta] = field(default_factory=list)

    def add(self, delta: RelationshipDelta) -> None:
        self.deltas.append(delta)

    def for_character(
        self, character: str, window: int = 0
    ) -> list[RelationshipDelta]:
        """Get all deltas involving a character, optionally limited to recent N."""
        results = [
            d
            for d in self.deltas
            if d.character_a == character or d.character_b == character
        ]
        if window > 0:
            results = results[-window:]
        return results

    def for_relationship(
        self, a: str, b: str
    ) -> list[RelationshipDelta]:
        """Get full history of a specific relationship."""
        return [
            d
            for d in self.deltas
            if (d.character_a == a and d.character_b == b)
            or (d.character_a == b and d.character_b == a)
        ]


class RelationshipDeltaTracker:
    """Tracks relationship changes and provides sentiment analysis."""

    def __init__(self, store: RelationshipDeltaStore | None = None) -> None:
        self.store = store or RelationshipDeltaStore()

    def record_delta(
        self,
        a: str,
        b: str,
        old_rel: RelationKind,
        new_rel: RelationKind,
        trigger: str,
        chapter_num: int = 0,
    ) -> RelationshipDelta:
        """Record a relationship change."""
        delta = RelationshipDelta(
            character_a=a,
            character_b=b,
            old_relation=old_rel,
            new_relation=new_rel,
            trigger_event=trigger,
            chapter_num=chapter_num,
        )
        self.store.add(delta)
        return delta

    def recent_changes(
        self, character: str, window: int = 5
    ) -> list[RelationshipDelta]:
        """Get recent relationship shifts for a character."""
        return self.store.for_character(character, window=window)

    def relationship_timeline(self, a: str, b: str) -> list[RelationshipDelta]:
        """Get full history of a specific relationship."""
        return self.store.for_relationship(a, b)

    def current_sentiment(self, a: str, b: str) -> float:
        """Aggregate sentiment (-1 to 1) based on recent deltas."""
        deltas = self.store.for_relationship(a, b)
        if not deltas:
            return 0.0

        # Use the most recent delta's new relation as the current sentiment
        latest = deltas[-1]
        return _RELATION_SENTIMENT.get(latest.new_relation, 0.0)

    def net_relationship_volatility(self, character: str) -> float:
        """Measure how much a character's relationships have changed (0-1)."""
        deltas = self.store.for_character(character)
        if not deltas:
            return 0.0

        # Count significant changes (changes that cross the neutral boundary)
        significant_changes = 0
        for d in deltas:
            old_sent = _RELATION_SENTIMENT.get(d.old_relation, 0.0)
            new_sent = _RELATION_SENTIMENT.get(d.new_relation, 0.0)
            if old_sent * new_sent < 0 or abs(new_sent - old_sent) > 0.6:
                significant_changes += 1

        return min(1.0, significant_changes / max(1, len(deltas)))

    def relationship_pressure_adjustment(
        self, a: str, b: str, current_relation: RelationKind
    ) -> float:
        """Return a pressure adjustment based on relationship trajectory.

        Positive = increasing tension, Negative = decreasing tension.
        """
        deltas = self.store.for_relationship(a, b)

        # Get the last few deltas to see trajectory
        recent = deltas[-3:] if len(deltas) >= 3 else deltas
        if not recent:
            return 0.0

        # Check if the relationship is trending negative
        trending_down = 0
        for d in recent:
            old_sent = _RELATION_SENTIMENT.get(d.old_relation, 0.0)
            new_sent = _RELATION_SENTIMENT.get(d.new_relation, 0.0)
            if new_sent < old_sent:
                trending_down += 1

        ratio = trending_down / max(1, len(recent))
        return ratio * 0.3  # max +/- 0.3 pressure adjustment

    def relationship_map(self, character: str) -> dict[str, float]:
        """Get current sentiment for all relationships of a character."""
        deltas = self.store.for_character(character)
        sentiments: dict[str, float] = {}

        for d in deltas:
            other = d.character_b if d.character_a == character else d.character_a
            sentiments[other] = _RELATION_SENTIMENT.get(d.new_relation, 0.0)

        return sentiments

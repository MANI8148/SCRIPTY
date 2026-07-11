"""World conflict registry — conflict tracking."""
from __future__ import annotations

from typing import Any

from backend.v2.types import WorldConstraints, GenerationRequest


class ConflictRegistry:
    """Tracks world-level conflicts (political, social, personal)."""

    def build(self, base: WorldConstraints, request: GenerationRequest) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        era = (base.era or "historical").lower()
        if "colonial" in era:
            conflicts.append(
                {
                    "name": "resistance vs empire",
                    "description": "local resistance against colonial administration",
                    "parties": ["the resistance", "the colonial administration"],
                    "intensity": 0.7,
                }
            )
        conflicts.append(
            {
                "name": "social tension",
                "description": "tension between established order and change",
                "parties": ["traditionalists", "reformers"],
                "intensity": 0.4,
            }
        )
        return conflicts

    def register(self, conflicts: list[dict[str, Any]], new_conflict: dict[str, Any]) -> list[dict[str, Any]]:
        conflicts.append(new_conflict)
        return conflicts

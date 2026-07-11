"""World drift detector — contradiction detection.

Compares two WorldConstraints snapshots (before/after) to flag
contradictions in objective world truth. Also validates invariants.
"""
from __future__ import annotations

from typing import Any

from backend.v2.types import WorldConstraints


class WorldDriftDetector:
    """Detects contradictions between world-state snapshots."""

    def detect(self, before: WorldConstraints, after: WorldConstraints) -> list[str]:
        issues: list[str] = []
        if before is None or after is None:
            return issues
        if before.era != after.era:
            issues.append(f"era drift: {before.era} -> {after.era}")
        if before.tech_level != after.tech_level:
            issues.append(
                f"tech_level drift: {before.tech_level} -> {after.tech_level}"
            )
        if before.year != after.year:
            issues.append(f"year drift: {before.year} -> {after.year}")
        return issues

    def check_constraints(self, world: WorldConstraints) -> list[str]:
        issues: list[str] = []
        if not world.location_description:
            issues.append("missing location_description")
        if world.year <= 0:
            issues.append("invalid year")
        return issues

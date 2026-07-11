"""World politics builder — factions, alliances, power structures.

Produces a dict describing the political landscape for a given world.
Defensive: never raises; returns sensible defaults for any era.
"""
from __future__ import annotations

from typing import Any

from backend.v2.types import WorldConstraints, GenerationRequest


class PoliticsBuilder:
    """Builds political structure (factions, alliances, power) for a world."""

    def build(self, base: WorldConstraints, request: GenerationRequest) -> dict[str, Any]:
        era = (base.era or "historical").lower()
        factions = self._factions_for_era(era)
        return {
            "factions": factions,
            "alliances": self._alliances(factions),
            "power_structures": self._power_structures(era),
            "ruling_entity": factions[0]["name"] if factions else "the local authority",
        }

    def _factions_for_era(self, era: str) -> list[dict[str, str]]:
        common = [
            {"name": "the crown", "ideology": "centralized rule"},
            {"name": "the merchants' guild", "ideology": "free trade"},
            {"name": "the clergy", "ideology": "religious authority"},
        ]
        if "colonial" in era:
            common.append(
                {"name": "the colonial administration", "ideology": "imperial control"}
            )
        if "digital" in era:
            common.append(
                {"name": "the civic council", "ideology": "representative governance"}
            )
        return common

    def _alliances(self, factions: list[dict[str, str]]) -> list[dict[str, str]]:
        if len(factions) >= 2:
            return [
                {
                    "between": [factions[0]["name"], factions[1]["name"]],
                    "type": "tactical",
                }
            ]
        return []

    def _power_structures(self, era: str) -> list[str]:
        if "colonial" in era:
            return ["viceroy", "district collector", "local raja"]
        if "digital" in era:
            return ["elected government", "civil service", "judiciary"]
        return ["monarch", "council of elders", "regional governor"]

"""World culture builder — social norms, taboos, traditions."""
from __future__ import annotations

from typing import Any

from backend.v2.types import WorldConstraints, GenerationRequest


class CultureBuilder:
    """Builds cultural structure (norms, taboos, traditions) for a world."""

    def build(self, base: WorldConstraints, request: GenerationRequest) -> dict[str, Any]:
        era = (base.era or "historical").lower()
        norms = ["hospitality to strangers", "respect for elders"]
        taboos = ["speaking against the ruler"]
        traditions = ["seasonal festivals", "oral storytelling"]
        if "colonial" in era:
            taboos.append("open defiance of colonial law")
        if "digital" in era:
            traditions.append("global connectedness")
        return {
            "social_norms": norms,
            "taboos": taboos,
            "traditions": traditions,
            "gender_roles": "patriarchal by default",
        }

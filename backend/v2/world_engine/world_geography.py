"""World geography builder — terrain, climate, regions."""
from __future__ import annotations

from typing import Any

from backend.v2.types import WorldConstraints, GenerationRequest


class GeographyBuilder:
    """Builds geographic profile (terrain, climate, regions) for a world."""

    def build(self, base: WorldConstraints, request: GenerationRequest) -> dict[str, Any]:
        era = (base.era or "historical").lower()
        loc = (base.location_description or "").lower()

        terrain = "plains"
        if any(k in loc for k in ("forest", "woods")):
            terrain = "forest"
        elif any(k in loc for k in ("mountain", "hill")):
            terrain = "mountain"
        elif any(k in loc for k in ("river", "coast", "sea")):
            terrain = "coastal"

        return {
            "terrain": terrain,
            "climate": "tropical" if "colonial" in era else "temperate",
            "regions": [base.location_description or "the region"],
            "notable_features": ["the old fort", "the market square"],
        }

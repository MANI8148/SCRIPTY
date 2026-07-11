"""World economy builder — resources, trade, currency."""
from __future__ import annotations

from typing import Any

from backend.v2.types import WorldConstraints, GenerationRequest


class EconomyBuilder:
    """Builds economic profile (currency, resources, trade) for a world."""

    def build(self, base: WorldConstraints, request: GenerationRequest) -> dict[str, Any]:
        era = (base.era or "historical").lower()
        currency = "rupee" if ("colonial" in era or "digital" in era) else "local coin"
        resources = ["grain", "textiles", "livestock"]
        if "digital" in era:
            resources.append("software talent")
        return {
            "currency": currency,
            "resources": resources,
            "trade_goods": ["spices", "cotton", "tea"],
            "markets": ["the bazaar", "the river port"],
        }

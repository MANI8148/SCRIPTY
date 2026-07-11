"""
SCRIPTY v2 — WorldState
Single source of truth for world constraints. Extended by WorldEngine.
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from backend.external.location_engine import LocationEngine
from backend.cache.cache_layer import CacheLayer
from backend.utils.india_timeline import IndiaTimeline
from backend.v2.types import WorldConstraints, GenerationRequest


class WorldState:
    """
    Builds WorldConstraints from location, year, and context.
    This is the single source of truth for world data.
    WorldEngine extends this and enriches with politics/culture/tech/economy/geography.
    """

    def __init__(self, cache_layer: Optional[CacheLayer] = None):
        self.cache_layer = cache_layer or CacheLayer()
        self.loc_engine = LocationEngine(cache_layer=self.cache_layer)

    async def build_constraints(self, request_or_location=None, year: int = 1920, **kwargs) -> WorldConstraints:
        """
        Build world constraints from generation request or location/year kwargs.
        This is the canonical method - WorldEngine delegates to this internally.
        Supports both:
          - build_constraints(request)  where request is a GenerationRequest
          - build_constraints(location="Hyderabad", year=1920) for test convenience
        """
        # Handle kwargs-style calls (for test compatibility)
        if request_or_location is not None and isinstance(request_or_location, str):
            # build_constraints("Hyderabad", year=1920) or build_constraints(location="Hyderabad", year=1920)
            filtered = {k: v for k, v in kwargs.items() if k != "location" and k in GenerationRequest.__dataclass_fields__}
            request = GenerationRequest(location=request_or_location, year=year, **filtered)
        elif request_or_location is not None and hasattr(request_or_location, 'location'):
            request = request_or_location
        else:
            loc = kwargs.pop("location", str(request_or_location or "unknown"))
            filtered = {k: v for k, v in kwargs.items() if k in GenerationRequest.__dataclass_fields__}
            request = GenerationRequest(location=loc, year=year, **filtered)

        loc_context = await self.loc_engine.get_context(
            request.location, request.location_type
        )
        time_ctx = IndiaTimeline.get_temporal_context(request.year)

        era = getattr(request, 'setting_period', '') or time_ctx.get("era", "historical")
        tech_level = time_ctx.get("tech_level") or time_ctx.get("tech", "pre-industrial")
        tone = time_ctx.get("tone", "serious")
        infrastructure = time_ctx.get("infrastructure", ["buildings", "roads"])
        transport = time_ctx.get("transport", ["walking", "riding"])

        location_description = loc_context.get("description", f"A place called {request.location}")
        if "display_name" in loc_context:
            location_description = loc_context["display_name"]

        return WorldConstraints(
            era=era,
            tech_level=tech_level,
            tone=tone,
            infrastructure=infrastructure,
            transport=transport,
            location_description=location_description,
            year=request.year,
        )

    def to_generation_context(self, constraints: WorldConstraints) -> dict[str, Any]:
        """Delegate to WorldConstraints.to_generation_context()."""
        return constraints.to_generation_context()

    def enrich_constraints(self, base: WorldConstraints, request: GenerationRequest) -> WorldConstraints:
        """
        Hook for WorldEngine to enrich with politics, culture, tech, economy, geography.
        Default implementation returns base unchanged.
        """
        return base
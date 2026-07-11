"""
SCRIPTY v2 — WorldEngine
Extends WorldState (single source of truth) and enriches with
politics / culture / tech / economy / geography / conflicts.

(B2 FIX) WorldEngine.build() delegates to WorldState.build_constraints()
internally and is the single source of truth for WorldConstraints.
"""
from __future__ import annotations

from typing import Optional

from backend.v2.world_state import WorldState
from backend.v2.world_engine.world_politics import PoliticsBuilder
from backend.v2.world_engine.world_culture import CultureBuilder
from backend.v2.world_engine.world_tech import TechBuilder
from backend.v2.world_engine.world_economy import EconomyBuilder
from backend.v2.world_engine.world_geography import GeographyBuilder
from backend.v2.world_engine.world_conflict_registry import ConflictRegistry
from backend.v2.world_engine.world_drift_detector import WorldDriftDetector
from backend.v2.types import WorldConstraints, GenerationRequest


class WorldEngine(WorldState):
    """
    Rich world state container.

    Extends (does NOT duplicate) WorldState. ``build()`` is the single
    source of truth: it calls ``WorldState.build_constraints()`` and
    enriches the resulting ``WorldConstraints`` with world detail.
    """

    def __init__(self, cache_layer: Optional[object] = None, world_state: Optional[WorldState] = None):
        # world_state arg accepted for API symmetry but WorldEngine IS a WorldState
        super().__init__(cache_layer=cache_layer)
        self._politics = PoliticsBuilder()
        self._culture = CultureBuilder()
        self._tech = TechBuilder()
        self._economy = EconomyBuilder()
        self._geography = GeographyBuilder()
        self._conflicts = ConflictRegistry()
        self._drift = WorldDriftDetector()

    async def build(self, request) -> WorldConstraints:
        """
        Single source of truth. Delegates base constraint construction to
        WorldState, then enriches with politics/culture/tech/economy/
        geography/conflicts.
        """
        base = await super().build_constraints(request)
        return self.enrich_constraints(base, request)

    def enrich_constraints(
        self, base: WorldConstraints, request: GenerationRequest
    ) -> WorldConstraints:
        """Attach world-detail dicts produced by the builders."""
        base.politics = self._politics.build(base, request)
        base.culture = self._culture.build(base, request)
        base.economy = self._economy.build(base, request)
        base.geography = self._geography.build(base, request)
        base.conflicts = self._conflicts.build(base, request)
        try:
            base.tech = self._tech.build(base, request)
        except Exception:
            # Never let enrichment break world construction.
            pass
        return base

    @property
    def drift_detector(self) -> WorldDriftDetector:
        return self._drift

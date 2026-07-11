"""
SCRIPTY v2 — ArcPlanner
Orchestrator producing the StoryArc -> ChapterArc -> SceneObjective
hierarchy (B3 FIX). Delegates per-chapter SceneObjective generation to
StoryPlanner and wraps the results in an arc-aware StoryPlan.
"""
from __future__ import annotations

from typing import Optional

from backend.v2.story_planner import StoryPlanner
from backend.v2.types import (
    ChapterArc,
    GenerationRequest,
    StoryMode,
    StoryPlan,
    WorldConstraints,
)
from backend.v2.arc_planner.story_arc import StoryArcBuilder
from backend.v2.arc_planner.chapter_arc import ChapterArcBuilder
from backend.v2.arc_planner.foreshadowing_engine import ForeshadowingEngine
from backend.v2.arc_planner.objective_hierarchy import ObjectiveHierarchyBuilder


class ArcPlanner:
    """
    Produces a full StoryPlan: StoryArc -> list[ChapterArc] -> SceneObjective[].

    SHORT mode collapses to a single ChapterArc. CHAPTER/BOOK produce the
    full chapter hierarchy. Replaces/augments StoryPlanner as the planning
    entry point for the engine.
    """

    def __init__(
        self,
        story_planner: Optional[StoryPlanner] = None,
        story_builder: Optional[StoryArcBuilder] = None,
        chapter_builder: Optional[ChapterArcBuilder] = None,
        foreshadowing: Optional[ForeshadowingEngine] = None,
        hierarchy: Optional[ObjectiveHierarchyBuilder] = None,
    ) -> None:
        self._story_planner = story_planner or StoryPlanner()
        self._story_builder = story_builder or StoryArcBuilder()
        self._chapter_builder = chapter_builder or ChapterArcBuilder()
        self._foreshadowing = foreshadowing or ForeshadowingEngine()
        self._hierarchy = hierarchy or ObjectiveHierarchyBuilder()

    def plan(
        self,
        request: GenerationRequest,
        world: Optional[WorldConstraints] = None,
    ) -> StoryPlan:
        mode = request.story_mode
        total = request.chapter_count if mode == StoryMode.BOOK else 1
        character_count = len(getattr(request, "characters", []) or [])

        chapter_arcs: list[ChapterArc] = []
        for ch in range(1, total + 1):
            objectives = self._story_planner.plan_chapter(
                chapter_num=ch,
                total_chapters=total,
                world=world,
                story_mode=mode,
                character_count=character_count,
            )
            arc = self._chapter_builder.build(ch, mode, objectives, world)
            chapter_arcs.append(arc)

        # Setup/payoff registration (mutates foreshadowing_elements).
        self._foreshadowing.register(chapter_arcs)

        # Build the top-level story arc and goal tree.
        story_arc = self._story_builder.build(chapter_arcs, total, mode)
        self._hierarchy.build(chapter_arcs, request)

        return StoryPlan(
            story_arc=story_arc,
            chapters=chapter_arcs,
            total_chapters=total,
        )

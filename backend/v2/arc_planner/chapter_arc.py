"""ChapterArc builder — per-chapter arc."""
from __future__ import annotations

from typing import Any

from backend.v2.types import ArcPhase, ChapterArc, SceneObjective, StoryMode, WorldConstraints


class ChapterArcBuilder:
    """Builds a ChapterArc from a list of SceneObjectives."""

    _THEMES = [
        "origins",
        "rising action",
        "complication",
        "turning point",
        "climax",
        "fallout",
        "resolution",
    ]

    def build(
        self,
        chapter_num: int,
        mode: StoryMode,
        objectives: list[SceneObjective],
        world: WorldConstraints | None = None,
    ) -> ChapterArc:
        tension_curve = [obj.required_tension for obj in objectives]
        theme = self._theme_for_chapter(chapter_num, mode)
        key_revelations = [
            obj.purpose for obj in objectives if "reveal" in obj.resolution_goal.lower()
        ]
        character_focus = list(
            dict.fromkeys([c for obj in objectives for c in obj.characters_involved])
        )
        return ChapterArc(
            chapter_num=chapter_num,
            phase=self._phase(chapter_num, mode),
            objectives=objectives,
            theme=theme,
            tension_curve=tension_curve,
            key_revelations=key_revelations,
            character_focus=character_focus,
        )

    def _phase(self, chapter_num: int, mode: StoryMode) -> ArcPhase:
        if mode == StoryMode.SHORT:
            return ArcPhase.RISING
        # Approximate narrative phase from chapter position.
        if chapter_num <= 1:
            return ArcPhase.CALM
        return ArcPhase.RISING

    def _theme_for_chapter(self, chapter_num: int, mode: StoryMode) -> str:
        if mode == StoryMode.SHORT:
            return "inciting moment"
        idx = (chapter_num - 1) % len(self._THEMES)
        return self._THEMES[idx]

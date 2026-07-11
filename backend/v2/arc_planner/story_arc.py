"""StoryArc builder — 3-act / 5-act structure."""
from __future__ import annotations

from typing import Any

from backend.v2.types import ChapterArc, StoryArc, StoryMode


class StoryArcBuilder:
    """Assembles a StoryArc from per-chapter arcs."""

    def build(
        self,
        chapters: list[ChapterArc],
        total_chapters: int,
        mode: StoryMode,
    ) -> StoryArc:
        if mode == StoryMode.SHORT:
            structure_type = "single_act"
        elif total_chapters >= 5:
            structure_type = "five_act"
        else:
            structure_type = "three_act"

        global_tension: list[float] = []
        for ch in chapters:
            global_tension.extend(ch.tension_curve or [0.5])

        premise = chapters[0].theme if chapters else ""
        return StoryArc(
            arcs=chapters,
            total_chapters=total_chapters,
            structure_type=structure_type,
            premise=premise,
            global_tension_curve=global_tension,
        )

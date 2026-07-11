"""Objective hierarchy — goal tree mapping character goals to scene objectives."""
from __future__ import annotations

from typing import Any

from backend.v2.types import ChapterArc, GenerationRequest


class ObjectiveHierarchyBuilder:
    """Builds a goal tree linking character goals to scene objectives."""

    def build(
        self, chapters: list[ChapterArc], request: GenerationRequest
    ) -> dict[str, Any]:
        tree: dict[str, Any] = {
            "root": getattr(request, "storyline", None)
            or getattr(request, "theme", None)
            or "the story",
            "characters": {},
        }
        goals_by_char: dict[str, list[str]] = {}
        for ch in chapters:
            for obj in ch.objectives:
                for char in obj.characters_involved:
                    goals_by_char.setdefault(char, []).append(obj.purpose)

        for char, purposes in goals_by_char.items():
            tree["characters"][char] = {"goals": purposes}
        return tree

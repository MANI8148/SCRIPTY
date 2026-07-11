"""Foreshadowing engine — setup/payoff registration."""
from __future__ import annotations

from typing import Any

from backend.v2.types import ChapterArc


class ForeshadowingEngine:
    """Registers foreshadowing setups (early) and payoffs (late)."""

    _SETUP_POOL = [
        "a sealed letter",
        "a stranger's warning",
        "a forgotten map",
        "an old grudge",
    ]

    def register(self, chapters: list[ChapterArc]) -> list[ChapterArc]:
        """Tag early objectives with foreshadowing elements and later ones
        with payoff markers. Returns the (mutated) chapter list."""
        if len(chapters) < 2:
            return chapters
        mid = max(1, len(chapters) // 2)
        for i, ch in enumerate(chapters):
            for obj in ch.objectives:
                if i < mid:
                    token = self._SETUP_POOL[obj.chapter_num % len(self._SETUP_POOL)]
                    if token not in obj.foreshadowing_elements:
                        obj.foreshadowing_elements.append(token)
                else:
                    # Payoff: a setup from an earlier chapter is realized.
                    if obj.foreshadowing_elements:
                        obj.resolution_goal = (
                            obj.resolution_goal or "resolve the foreshadowed thread"
                        )
        return chapters

    def plan_setup_payoff(self, total_chapters: int) -> dict[str, Any]:
        mid = max(2, total_chapters // 2)
        return {
            "setup_chapters": list(range(1, mid)),
            "payoff_chapters": list(range(mid, total_chapters + 1)),
            "gap": max(1, total_chapters // 3),
        }

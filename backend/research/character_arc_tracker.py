from __future__ import annotations

from enum import Enum


class ArcStage(Enum):
    unaware = 0
    discovering = 1
    confronting = 2
    resolving = 3


class CharacterArcTracker:
    """Tracks monotonic character arc stage progression by chapter."""

    def __init__(self) -> None:
        self._progression: dict[str, list[tuple[int, ArcStage]]] = {}

    def track_progression(self, character: str, chapter_num: int, stage: ArcStage | str) -> None:
        if isinstance(stage, str):
            stage = ArcStage[stage]
        entries = self._progression.setdefault(character, [])
        if entries and stage.value < entries[-1][1].value:
            stage = entries[-1][1]
        if entries and entries[-1][0] == chapter_num:
            entries[-1] = (chapter_num, stage)
        else:
            entries.append((chapter_num, stage))

    def detect_stagnation(self, character: str) -> bool:
        entries = self._progression.get(character, [])
        if len(entries) < 4:
            return False
        return len({stage for _, stage in entries[-4:]}) == 1

    def get_arc_progression(self, character: str) -> list[tuple[int, ArcStage]]:
        return list(self._progression.get(character, []))

    def current_stage(self, character: str) -> ArcStage | None:
        entries = self._progression.get(character, [])
        return entries[-1][1] if entries else None

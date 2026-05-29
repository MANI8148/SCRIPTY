from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ArcPoint:
    chapter_num: int
    scene_num: int
    actual_tension: float
    planned_tension: float


@dataclass(frozen=True)
class TensionFactors:
    conflict_intensity: float = 0.0
    stakes: float = 0.0
    uncertainty: float = 0.0
    emotional_pressure: float = 0.0


class EmotionalArcModel:
    def __init__(self) -> None:
        self._arc_points: list[ArcPoint] = []
        self.tension_curve: list[tuple[int, int, float, TensionFactors]] = []

    def record(
        self,
        chapter_num: int,
        scene_num: int,
        actual_tension: float,
        planned_tension: float,
    ) -> None:
        """Record an arc point."""
        if self._arc_points:
            last = self._arc_points[-1]
            if chapter_num < last.chapter_num or (chapter_num == last.chapter_num and scene_num <= last.scene_num):
                raise ValueError("Arc points must be recorded sequentially.")
        self._arc_points.append(
            ArcPoint(chapter_num, scene_num, actual_tension, planned_tension)
        )
        self.tension_curve.append(
            (chapter_num, scene_num, actual_tension, self.compute_scene_tension("", {})[1])
        )

    def compute_scene_tension(self, scene_content: str, context: dict | None = None) -> tuple[float, TensionFactors]:
        words = set(re.findall(r"[a-zA-Z']+", scene_content.lower()))
        factors = TensionFactors(
            conflict_intensity=self._keyword_score(words, {"conflict", "fight", "threat", "danger", "battle"}),
            stakes=self._keyword_score(words, {"stakes", "protect", "risk", "future", "everything", "power"}),
            uncertainty=self._keyword_score(words, {"unknown", "secret", "maybe", "uncertain", "mystery", "hidden"}),
            emotional_pressure=self._keyword_score(words, {"fear", "desperate", "angry", "grief", "hope", "doubt"}),
        )
        target = float((context or {}).get("target_tension", 0.0))
        score = 0.25 * (
            factors.conflict_intensity + factors.stakes + factors.uncertainty + factors.emotional_pressure
        )
        if target:
            score = (score + target) / 2
        return round(max(0.0, min(1.0, score)), 6), factors

    def record_scene(self, chapter_num: int, scene_num: int, scene_content: str, context: dict | None = None) -> float:
        score, factors = self.compute_scene_tension(scene_content, context)
        self.tension_curve.append((chapter_num, scene_num, score, factors))
        return score

    def validate_tension_curve(self) -> list[str]:
        logger = logging.getLogger(__name__)
        scores = [point[2] for point in self.tension_curve]
        if len(scores) < 3:
            return []
        mean = sum(scores) / len(scores)
        variance = sum((score - mean) ** 2 for score in scores) / len(scores)
        peak_index = max(range(len(scores)), key=scores.__getitem__)
        issues: list[str] = []
        if variance < 0.1:
            issues.append("flat curve: variance < 0.1")
        if peak_index < int(len(scores) * 0.7):
            issues.append("early peak: peak occurs before final 30%")
        if max(scores) < 0.65:
            issues.append("missing climax: peak tension below 0.65")
        for issue in issues:
            logger.warning("tension_curve_warning", extra={"issue": issue})
        return issues

    def _keyword_score(self, words: set[str], keywords: set[str]) -> float:
        if not words:
            return 0.0
        return min(1.0, len(words & keywords) / 3)

    def compute_mad(self) -> float:
        """Compute mean absolute deviation between actual and planned tension."""
        if not self._arc_points:
            return 0.0
        deviations = [
            abs(p.actual_tension - p.planned_tension) for p in self._arc_points
        ]
        return sum(deviations) / len(deviations)

    def is_collapsed(self, threshold: float = 0.30) -> bool:
        """Return True if MAD exceeds threshold (arc collapse)."""
        return self.compute_mad() > threshold

    def get_arc_series(self) -> list[ArcPoint]:
        """Return all recorded arc points in order."""
        return list(self._arc_points)

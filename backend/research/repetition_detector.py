from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class RepetitionReport:
    phrase_repetition_rate: float
    opening_repetition_rate: float
    structure_repetition_rate: float
    pattern_repetition_rate: float
    warnings: list[dict] = field(default_factory=list)

    @property
    def diversity_score(self) -> float:
        penalty = (
            0.35 * self.phrase_repetition_rate
            + 0.25 * self.opening_repetition_rate
            + 0.20 * self.structure_repetition_rate
            + 0.20 * self.pattern_repetition_rate
        )
        return round(max(0.0, 1.0 - penalty), 6)


class RepetitionDetector:
    def _tokens(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z][a-zA-Z']*", text.lower())

    def phrase_repetition_rate(self, texts: list[str], n: int = 3) -> float:
        tokens = self._tokens(" ".join(texts))
        grams = list(zip(*(tokens[i:] for i in range(n))))
        if not grams:
            return 0.0
        counts = Counter(grams)
        return sum(1 for count in counts.values() if count > 1) / len(counts)

    def opening_repetition_rate(self, texts: list[str], words: int = 4) -> float:
        openings = [tuple(self._tokens(text)[:words]) for text in texts if self._tokens(text)]
        if not openings:
            return 0.0
        counts = Counter(openings)
        return sum(count - 1 for count in counts.values() if count > 1) / len(openings)

    def structure_repetition_rate(self, scene_types: list[str], width: int = 3) -> float:
        if len(scene_types) < width:
            return 0.0
        grams = list(zip(*(scene_types[i:] for i in range(width))))
        counts = Counter(grams)
        return sum(1 for count in counts.values() if count > 1) / len(counts)

    def pattern_repetition_rate(self, beats: list[str], width: int = 3) -> float:
        return self.structure_repetition_rate(beats, width)

    def analyze(self, texts: list[str], scene_types: list[str] | None = None, beats: list[str] | None = None) -> RepetitionReport:
        scene_types = scene_types or []
        beats = beats or []
        report = RepetitionReport(
            phrase_repetition_rate=round(self.phrase_repetition_rate(texts), 6),
            opening_repetition_rate=round(self.opening_repetition_rate(texts), 6),
            structure_repetition_rate=round(self.structure_repetition_rate(scene_types), 6),
            pattern_repetition_rate=round(self.pattern_repetition_rate(beats), 6),
        )
        for key in (
            "phrase_repetition_rate",
            "opening_repetition_rate",
            "structure_repetition_rate",
            "pattern_repetition_rate",
        ):
            if getattr(report, key) > 0.4:
                report.warnings.append({"type": key, "value": getattr(report, key)})
        return report

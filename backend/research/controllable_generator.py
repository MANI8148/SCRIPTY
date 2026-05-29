from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConditioningSpec:
    genre: str | None = None
    tone: str | None = None
    emotional_target: float | None = None
    style_keywords: tuple[str, ...] = field(default_factory=tuple)
    pacing: float = 1.0


class ControllableGenerator:
    def score_template(self, template: str, spec: ConditioningSpec) -> float:
        tokens = set(template.lower().split())
        keywords = set(word.lower() for word in spec.style_keywords)
        if spec.genre:
            keywords.add(spec.genre.lower())
        if spec.tone:
            keywords.add(spec.tone.lower())
        return len(tokens & keywords) / max(1, len(keywords))

    def filter_templates(self, templates: list[str], spec: ConditioningSpec) -> list[str]:
        return sorted(templates, key=lambda template: self.score_template(template, spec), reverse=True)

    def apply_pacing(self, base: int, spec: ConditioningSpec) -> int:
        return max(1, int(base * spec.pacing))


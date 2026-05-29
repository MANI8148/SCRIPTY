from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend.research.scene_dataset_generator import SCENE_TYPES

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SceneConstraint:
    constraint_type: str
    parameters: dict = field(default_factory=dict)


class HybridSceneSelector:
    IMPOSSIBLE_TRANSITIONS = {
        ("resolution", "setup"),
        ("transition", "setup"),
    }

    def __init__(self, ml_weight: float = 0.70, rule_weight: float = 0.30) -> None:
        self.ml_weight = ml_weight
        self.rule_weight = rule_weight
        self.decision_stats = {"ml_selected": 0, "rule_override": 0, "total": 0}

    def select_next_scene(
        self,
        ml_probs: dict[str, float],
        rule_constraints: list[SceneConstraint] | None = None,
        *,
        previous_scene_types: list[str] | None = None,
        current_beat: str | None = None,
    ) -> str:
        previous_scene_types = [self._normalise(item) for item in (previous_scene_types or [])]
        constraints = rule_constraints or []
        blocked = self.blocked_scene_types(constraints, previous_scene_types, current_beat)
        scores = self._combined_scores(ml_probs, constraints)
        for scene_type in blocked:
            scores[scene_type] = -1.0
        selected = max(scores, key=scores.__getitem__)
        ml_choice = max(self._normalise_distribution(ml_probs), key=self._normalise_distribution(ml_probs).__getitem__)
        self.decision_stats["total"] += 1
        if selected == ml_choice and selected not in blocked:
            self.decision_stats["ml_selected"] += 1
        else:
            self.decision_stats["rule_override"] += 1
        return selected

    def blocked_scene_types(
        self,
        constraints: list[SceneConstraint],
        previous_scene_types: list[str],
        current_beat: str | None = None,
    ) -> set[str]:
        blocked: set[str] = set()
        for constraint in constraints:
            if constraint.constraint_type == "max_consecutive":
                scene_type = self._normalise(constraint.parameters.get("scene_type", ""))
                limit = int(constraint.parameters.get("limit", 2))
                if scene_type and len(previous_scene_types) >= limit:
                    if all(item == scene_type for item in previous_scene_types[-limit:]):
                        blocked.add(scene_type)
            elif constraint.constraint_type == "forbid":
                blocked.update(self._normalise(item) for item in constraint.parameters.get("scene_types", []))
            elif constraint.constraint_type == "require_one_of":
                allowed = {self._normalise(item) for item in constraint.parameters.get("scene_types", [])}
                blocked.update(set(SCENE_TYPES) - allowed)
        if previous_scene_types:
            transition_from = current_beat or previous_scene_types[-1]
            for source, target in self.IMPOSSIBLE_TRANSITIONS:
                if transition_from == source:
                    blocked.add(target)
                    logger.info(
                        "impossible_transition_blocked",
                        extra={"source": source, "target": target},
                    )
        return blocked

    def default_constraints(self) -> list[SceneConstraint]:
        return [
            SceneConstraint("max_consecutive", {"scene_type": "action", "limit": 2}),
            SceneConstraint("max_consecutive", {"scene_type": "dialogue", "limit": 2}),
            SceneConstraint("max_consecutive", {"scene_type": "description", "limit": 2}),
        ]

    def ml_influence_rate(self) -> float:
        return self.decision_stats["ml_selected"] / max(1, self.decision_stats["total"])

    def _combined_scores(self, ml_probs: dict[str, float], constraints: list[SceneConstraint]) -> dict[str, float]:
        distribution = self._normalise_distribution(ml_probs)
        rule_scores = {scene_type: 1.0 for scene_type in SCENE_TYPES}
        for constraint in constraints:
            if constraint.constraint_type == "prefer":
                for scene_type in constraint.parameters.get("scene_types", []):
                    normalised = self._normalise(scene_type)
                    if normalised in rule_scores:
                        rule_scores[normalised] += float(constraint.parameters.get("boost", 0.5))
        max_rule = max(rule_scores.values()) or 1.0
        rule_scores = {scene_type: score / max_rule for scene_type, score in rule_scores.items()}
        return {
            scene_type: self.ml_weight * distribution[scene_type] + self.rule_weight * rule_scores[scene_type]
            for scene_type in SCENE_TYPES
        }

    def _normalise_distribution(self, ml_probs: dict[str, float]) -> dict[str, float]:
        cleaned = {scene_type: max(0.0, float(ml_probs.get(scene_type, 0.0))) for scene_type in SCENE_TYPES}
        total = sum(cleaned.values())
        if total <= 0:
            return {scene_type: 1.0 / len(SCENE_TYPES) for scene_type in SCENE_TYPES}
        return {scene_type: score / total for scene_type, score in cleaned.items()}

    def _normalise(self, value: object) -> str:
        if hasattr(value, "value"):
            value = value.value
        return str(value).lower()

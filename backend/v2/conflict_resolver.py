from __future__ import annotations

from backend.v2.types import (
    AgentState,
    Intention,
    SceneObjective,
    SceneType,
)


class ConflictResolver:
    """Arbitrates agent intentions into SceneObjectives.

    Replaces the dead DecisionTrace/EconomicActionDecision metadata-only flows.
    Every resolution directly modifies the SceneObjective that drives generation.
    """

    def resolve(
        self,
        agent_states: list[AgentState],
        base_objective: SceneObjective,
    ) -> SceneObjective:
        intentions: list[tuple[str, Intention | None]] = [
            (a.character.name, a.intention) for a in agent_states
        ]

        objective = base_objective

        conflicting = self._find_conflicts(intentions)
        if conflicting:
            objective = self._escalate_for_conflict(objective, conflicting)

        dominant = self._dominant_intention(intentions)
        if dominant:
            objective = self._adjust_for_intention(objective, dominant[0], dominant[1])

        objective.characters_involved = [
            name for name, _ in intentions if name not in ("", None)
        ]

        return objective

    def calculate_scene_type(
        self,
        agent_states: list[AgentState],
        base_type: SceneType,
    ) -> SceneType:
        total_pressure = sum(a.emotional_pressure for a in agent_states)
        avg_pressure = total_pressure / max(len(agent_states), 1)

        if avg_pressure > 0.7 and base_type != SceneType.ACTION:
            return SceneType.ACTION
        if avg_pressure > 0.4 and base_type == SceneType.DESCRIPTION:
            return SceneType.DIALOGUE
        return base_type

    def _find_conflicts(
        self,
        intentions: list[tuple[str, Intention | None]],
    ) -> list[tuple[str, str, str]]:
        conflicts: list[tuple[str, str, str]] = []
        for i, (name_a, intent_a) in enumerate(intentions):
            for name_b, intent_b in intentions[i + 1 :]:
                if intent_a and intent_b:
                    if intent_a.target == intent_b.target and intent_a.target:
                        conflicts.append(
                            (name_a, name_b, f"competing over {intent_a.target}")
                        )
                    if intent_a.goal != intent_b.goal and intent_a.urgency > 0.5:
                        conflicts.append(
                            (name_a, name_b, f"conflicting goals: {intent_a.goal} vs {intent_b.goal}")
                        )
        return conflicts

    def _escalate_for_conflict(
        self,
        objective: SceneObjective,
        conflicts: list[tuple[str, str, str]],
    ) -> SceneObjective:
        conflict_desc = "; ".join(f"{a} and {b}: {c}" for a, b, c in conflicts)
        return SceneObjective(
            purpose=f"{objective.purpose} — conflict: {conflict_desc}",
            characters_involved=objective.characters_involved,
            location=objective.location,
            conflict_type="active",
            required_tension=min(1.0, objective.required_tension + 0.3),
            target_scene_type=SceneType.ACTION
            if objective.target_scene_type != SceneType.INTROSPECTION
            else objective.target_scene_type,
            resolution_goal="resolve interpersonal conflict",
        )

    def _dominant_intention(
        self,
        intentions: list[tuple[str, Intention | None]],
    ) -> tuple[str, Intention] | None:
        valid = [(name, i) for name, i in intentions if i is not None]
        if not valid:
            return None
        valid.sort(key=lambda x: x[1].urgency, reverse=True)
        return valid[0]

    def _adjust_for_intention(
        self,
        objective: SceneObjective,
        name: str,
        intention: Intention,
    ) -> SceneObjective:
        return SceneObjective(
            purpose=f"{objective.purpose} — {name} {intention.action} to {intention.goal}",
            characters_involved=objective.characters_involved,
            location=objective.location,
            conflict_type=objective.conflict_type,
            required_tension=objective.required_tension,
            target_scene_type=objective.target_scene_type,
            resolution_goal=f"{intention.action} {intention.target}" if intention.target else objective.resolution_goal,
        )

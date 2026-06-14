"""MomentumExtraction — maintains narrative momentum across scenes.

Tracks velocity, tension trends, stakes trends, and character engagement.
Detects stagnation, optimizes pacing, and produces momentum reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, stdev
from typing import Any

from backend.v2.character_agent import CharacterAgent
from backend.v2.types import (
    GeneratedScene,
    SceneBlueprint,
    SceneObjective,
    SceneType,
)


# ---------------------------------------------------------------------------
# MomentumState — snapshot of current narrative momentum
# ---------------------------------------------------------------------------


@dataclass
class MomentumState:
    velocity: float  # 0-1, how fast the story is moving
    tension_trend: str  # rising, falling, plateau, oscillating
    stakes_trend: str  # rising, falling, steady
    character_momentum: dict[str, float] = field(default_factory=dict)
    scene_to_scene_momentum: list[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# MomentumExtractor — computes momentum from scene history
# ---------------------------------------------------------------------------


class MomentumExtractor:
    """Computes narrative momentum from scene history."""

    def compute_momentum(
        self,
        scene_history: list[GeneratedScene],
    ) -> MomentumState:
        """Compute full momentum state from scene history."""
        if not scene_history:
            return MomentumState(
                velocity=0.5,
                tension_trend="stable",
                stakes_trend="steady",
                character_momentum={},
                scene_to_scene_momentum=[],
            )

        # Compute scene-to-scene momentum transfers
        transfers = []
        for i in range(1, len(scene_history)):
            transfer = self.scene_to_scene_transfer(
                scene_history[i - 1],
                scene_history[i],
            )
            transfers.append(transfer)

        # Compute velocity from tension history
        tensions = [s.tension for s in scene_history]
        velocity = self.velocity_from_tension(tensions)

        # Determine tension trend
        tension_trend = self._determine_trend(tensions)

        # Determine stakes trend (approximate from tension variance)
        stakes_trend = self._determine_stakes_trend(tensions, velocity)

        # Compute per-character momentum
        char_momentum = self._compute_character_momentum(scene_history)

        return MomentumState(
            velocity=velocity,
            tension_trend=tension_trend,
            stakes_trend=stakes_trend,
            character_momentum=char_momentum,
            scene_to_scene_momentum=transfers,
        )

    def scene_to_scene_transfer(
        self,
        previous: GeneratedScene,
        current: GeneratedScene,
    ) -> float:
        """Compute momentum transfer between two consecutive scenes.

        Uses similarity, tension delta, and character overlap.
        Returns 0-1 where higher = stronger momentum transfer.
        """
        # Tension continuity (higher delta = lower transfer)
        tension_delta = abs(previous.tension - current.tension)
        tension_continuity = 1.0 - tension_delta

        # Character overlap
        prev_chars = set(previous.characters_involved)
        curr_chars = set(current.characters_involved)
        overlap = len(prev_chars & curr_chars)
        total = len(prev_chars | curr_chars)
        char_continuity = overlap / max(total, 1)

        # Scene type variety (same type = lower transfer)
        type_continuity = 1.0 if previous.scene_type == current.scene_type else 0.7

        # Combined score
        transfer = (
            tension_continuity * 0.4
            + char_continuity * 0.4
            + type_continuity * 0.2
        )

        return max(0.0, min(1.0, transfer))

    def velocity_from_tension(
        self,
        tension_history: list[float],
    ) -> float:
        """Compute narrative velocity from tension history.

        Velocity is higher when tension is changing (rising or falling).
        Velocity is lower when tension is flat.
        """
        if len(tension_history) < 2:
            return 0.5

        # Compute absolute changes
        deltas = [
            abs(tension_history[i] - tension_history[i - 1])
            for i in range(1, len(tension_history))
        ]

        avg_delta = mean(deltas)
        # Map average delta to 0-1 velocity
        velocity = min(1.0, avg_delta * 2.0)

        # Recent deltas matter more
        if len(deltas) >= 3:
            recent_deltas = deltas[-3:]
            recent_avg = mean(recent_deltas)
            recent_velocity = min(1.0, recent_avg * 2.0)
            velocity = velocity * 0.4 + recent_velocity * 0.6

        return velocity

    def detect_stagnation(
        self,
        scene_history: list[GeneratedScene],
        window: int = 3,
    ) -> bool:
        """Detect if the story is stagnating (tension not changing)."""
        if len(scene_history) < window:
            return False

        recent = scene_history[-window:]
        tensions = [s.tension for s in recent]

        # Stagnation if all tensions are within 5% of each other
        if len(tensions) >= 2:
            return max(tensions) - min(tensions) < 0.05

        return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _determine_trend(
        self,
        values: list[float],
    ) -> str:
        """Determine the trend direction of a sequence of values."""
        if len(values) < 3:
            return "stable"

        recent = values[-3:]
        deltas = [
            recent[i] - recent[i - 1]
            for i in range(1, len(recent))
        ]

        avg_delta = mean(deltas)

        if abs(avg_delta) < 0.03:
            return "plateau"

        # Check for oscillation
        if len(deltas) >= 2:
            signs = [1 if d >= 0 else -1 for d in deltas]
            if len(set(signs)) > 1:
                return "oscillating"

        if avg_delta > 0:
            return "rising"
        return "falling"

    def _determine_stakes_trend(
        self,
        tensions: list[float],
        velocity: float,
    ) -> str:
        """Determine stakes trend from tension and velocity."""
        if len(tensions) < 3:
            return "steady"

        # Rising tension + high velocity = rising stakes
        # Falling tension + high velocity = falling stakes
        # Low velocity = steady stakes
        trend = self._determine_trend(tensions)

        if velocity < 0.2:
            return "steady"

        if trend == "rising":
            return "rising"
        if trend == "falling":
            return "falling"

        return "steady"

    def _compute_character_momentum(
        self,
        scene_history: list[GeneratedScene],
    ) -> dict[str, float]:
        """Compute per-character engagement momentum."""
        char_scores: dict[str, list[float]] = {}

        for scene in scene_history:
            for char in scene.characters_involved:
                if char not in char_scores:
                    char_scores[char] = []
                char_scores[char].append(scene.tension)

        result: dict[str, float] = {}
        for char, tensions in char_scores.items():
            if tensions:
                # Momentum = average tension weighted by presence
                result[char] = mean(tensions)
            else:
                result[char] = 0.0

        return result


# ---------------------------------------------------------------------------
# MomentumOptimizer — optimizes scene blueprints based on momentum
# ---------------------------------------------------------------------------


class MomentumOptimizer:
    """Optimizes scene generation based on current momentum state."""

    def optimize(
        self,
        blueprint: SceneBlueprint,
        momentum: MomentumState,
    ) -> SceneBlueprint:
        """Modify scene blueprint to optimize narrative momentum."""
        objective = blueprint.objective

        # 1. If story is stagnating → increase tension, shift to ACTION
        if momentum.tension_trend == "plateau" or momentum.velocity < 0.3:
            objective = SceneObjective(
                purpose=objective.purpose,
                characters_involved=objective.characters_involved,
                location=objective.location,
                conflict_type="active",
                required_tension=min(1.0, objective.required_tension + 0.3),
                target_scene_type=SceneType.ACTION,
                resolution_goal="escalate stakes",
            )

        # 2. If story is too fast → add introspection
        elif momentum.velocity > 0.8:
            objective = SceneObjective(
                purpose=objective.purpose,
                characters_involved=objective.characters_involved,
                location=objective.location,
                conflict_type=objective.conflict_type,
                required_tension=max(0.0, objective.required_tension - 0.1),
                target_scene_type=SceneType.INTROSPECTION,
                resolution_goal="deepen character",
            )

        # 3. If tension is oscillating → smooth it
        elif momentum.tension_trend == "oscillating":
            # Aim for middle ground
            target_tension = 0.5
            if objective.required_tension > 0.7:
                target_tension = 0.4
            elif objective.required_tension < 0.3:
                target_tension = 0.6
            else:
                target_tension = objective.required_tension

            objective = SceneObjective(
                purpose=objective.purpose,
                characters_involved=objective.characters_involved,
                location=objective.location,
                conflict_type=objective.conflict_type,
                required_tension=target_tension,
                target_scene_type=objective.target_scene_type,
                resolution_goal=objective.resolution_goal,
            )

        # 4. If character momentum is low → put character in focus
        low_momentum_chars = [
            char for char, score in momentum.character_momentum.items()
            if score < 0.3
        ]
        if low_momentum_chars and momentum.tension_trend != "plateau":
            # Add a low-momentum character to this scene
            involved = list(objective.characters_involved)
            for char in low_momentum_chars:
                if char not in involved:
                    involved.append(char)
                    break
            objective = SceneObjective(
                purpose=objective.purpose,
                characters_involved=involved,
                location=objective.location,
                conflict_type=objective.conflict_type,
                required_tension=objective.required_tension,
                target_scene_type=objective.target_scene_type,
                resolution_goal=objective.resolution_goal,
            )

        return SceneBlueprint(
            objective=objective,
            agent_states=blueprint.agent_states,
            world=blueprint.world,
            retrieved_memories=blueprint.retrieved_memories,
        )


# ---------------------------------------------------------------------------
# MomentumReporter — produces human-readable momentum reports
# ---------------------------------------------------------------------------


class MomentumReporter:
    """Produces reports about narrative momentum."""

    def report(
        self,
        momentum: MomentumState,
        chapter_num: int,
    ) -> str:
        """Generate a human-readable momentum report for a chapter."""
        lines: list[str] = []
        lines.append(f"Momentum Report — Chapter {chapter_num}")
        lines.append("-" * 40)
        lines.append(f"  Velocity:        {momentum.velocity:.3f}")
        lines.append(f"  Tension Trend:   {momentum.tension_trend}")
        lines.append(f"  Stakes Trend:    {momentum.stakes_trend}")
        lines.append("")

        if momentum.character_momentum:
            lines.append("  Character Momentum:")
            for char, score in sorted(
                momentum.character_momentum.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                lines.append(f"    {char}: {score:.3f}")
            lines.append("")

        if momentum.scene_to_scene_momentum:
            avg_transfer = mean(momentum.scene_to_scene_momentum)
            lines.append(
                f"  Avg Scene-to-Scene Transfer: {avg_transfer:.3f}"
            )
            lines.append("")

        return "\n".join(lines)

    def momentum_summary(
        self,
        scene_history: list[GeneratedScene],
    ) -> dict:
        """Return a summary dict of momentum across all scenes."""
        if not scene_history:
            return {"scenes": 0}

        extractor = MomentumExtractor()
        momentum = extractor.compute_momentum(scene_history)

        return {
            "total_scenes": len(scene_history),
            "velocity": momentum.velocity,
            "tension_trend": momentum.tension_trend,
            "stakes_trend": momentum.stakes_trend,
            "avg_momentum_transfer": (
                mean(momentum.scene_to_scene_momentum)
                if momentum.scene_to_scene_momentum
                else 0.0
            ),
            "character_momentum": momentum.character_momentum,
        }

    def stagnation_warnings(
        self,
        scene_history: list[GeneratedScene],
    ) -> list[str]:
        """Return list of stagnation warnings."""
        warnings: list[str] = []
        extractor = MomentumExtractor()

        if extractor.detect_stagnation(scene_history, window=3):
            warnings.append(
                "Story is stagnating: tension has not changed "
                "in the last 3 scenes"
            )

        if len(scene_history) >= 4:
            tensions = [s.tension for s in scene_history[-4:]]
            if all(t < 0.2 for t in tensions):
                warnings.append(
                    "Low tension across last 4 scenes: "
                    "story may be losing momentum"
                )

        if len(scene_history) >= 3:
            types = [s.scene_type for s in scene_history[-3:]]
            if len(set(types)) == 1:
                warnings.append(
                    f"Last 3 scenes are all {types[0].value}: "
                    f"add scene type variety"
                )

        return warnings

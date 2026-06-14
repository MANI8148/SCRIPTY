"""EmotionalSpec — formal specification for emotional arcs across scenes.

Defines emotional beats per character, validates coherence of arcs,
and integrates emotional context into SceneBlueprint generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, stdev
from typing import Any

from backend.v2.character_agent import CharacterAgent
from backend.v2.types import (
    SceneBlueprint,
    SceneObjective,
    SceneType,
    WorldConstraints,
)


# ---------------------------------------------------------------------------
# Emotional Beat — a single emotional data point in a character's arc
# ---------------------------------------------------------------------------


@dataclass
class EmotionalBeat:
    character: str
    emotion: str  # anger, fear, joy, sadness, guilt, shame, jealousy, hope, desperation
    intensity: float  # 0-1
    trigger: str  # what caused this emotion
    beats_until_resolution: int  # how many scenes this emotion should persist


# ---------------------------------------------------------------------------
# Emotional Arc — full emotional trajectory for one character
# ---------------------------------------------------------------------------


@dataclass
class EmotionalArc:
    character: str
    beats: list[EmotionalBeat] = field(default_factory=list)
    dominant_emotion: str = "neutral"
    volatility: float = 0.0  # how quickly emotions shift (0=stable, 1=erratic)
    resolution_state: str = "unresolved"  # resolved, unresolved, transformed


# ---------------------------------------------------------------------------
# EmotionalSpecBuilder — builds emotional arcs from character data
# ---------------------------------------------------------------------------


# Trait → likely dominant emotion mapping
_TRAIT_EMOTION_MAP: dict[str, str] = {
    "brave": "hope",
    "cautious": "fear",
    "curious": "hope",
    "deceptive": "guilt",
    "ambitious": "jealousy",
    "kind": "joy",
    "loyal": "joy",
    "reckless": "desperation",
    "wise": "joy",
    "pious": "joy",
    "proud": "anger",
    "gentle": "sadness",
    "arrogant": "anger",
    "sly": "guilt",
    "patient": "hope",
    "angry": "anger",
    "bitter": "anger",
    "hopeful": "hope",
    "melancholic": "sadness",
    "mysterious": "fear",
    "charismatic": "joy",
    "compassionate": "sadness",
    "brash": "anger",
    "rude": "anger",
    "spiritual": "hope",
    "thoughtful": "sadness",
    "learned": "joy",
    "greedy": "jealousy",
    "jealous": "jealousy",
    "desperate": "desperation",
    "fearful": "fear",
    "ashamed": "shame",
    "guilty": "guilt",
}

# Trait → emotional volatility
_TRAIT_VOLATILITY: dict[str, float] = {
    "brave": 0.3,
    "cautious": 0.2,
    "curious": 0.4,
    "deceptive": 0.6,
    "ambitious": 0.5,
    "kind": 0.2,
    "loyal": 0.2,
    "reckless": 0.8,
    "wise": 0.1,
    "pious": 0.1,
    "proud": 0.5,
    "gentle": 0.2,
    "arrogant": 0.6,
    "sly": 0.5,
    "patient": 0.1,
    "angry": 0.7,
    "bitter": 0.4,
    "hopeful": 0.3,
    "melancholic": 0.2,
    "mysterious": 0.3,
    "charismatic": 0.3,
    "compassionate": 0.3,
    "brash": 0.7,
    "rude": 0.6,
    "spiritual": 0.1,
    "thoughtful": 0.2,
    "learned": 0.1,
    "greedy": 0.6,
    "jealous": 0.7,
    "desperate": 0.8,
    "fearful": 0.5,
    "ashamed": 0.3,
    "guilty": 0.4,
}

# Resolution styles per dominant emotion
_EMOTION_RESOLUTION: dict[str, str] = {
    "anger": "resolved",
    "fear": "transformed",
    "joy": "resolved",
    "sadness": "transformed",
    "guilt": "resolved",
    "shame": "transformed",
    "jealousy": "transformed",
    "hope": "resolved",
    "desperation": "resolved",
    "neutral": "resolved",
}


class EmotionalSpecBuilder:
    """Builds emotional arc specifications from character agents and world state."""

    def build_spec(
        self,
        agents: list[CharacterAgent],
        world: WorldConstraints,
        scene_count: int,
    ) -> list[EmotionalArc]:
        """Map emotional_pressure → emotional beats across scenes."""
        arcs: list[EmotionalArc] = []

        for agent in agents:
            beats: list[EmotionalBeat] = []
            traits_lower = [t.lower() for t in agent.character.traits]
            dominant = self._dominant_emotion(traits_lower)

            # Determine volatility from traits
            volatility = self._compute_volatility(traits_lower)

            # Project emotional beats across scenes
            for scene_idx in range(scene_count):
                progress = scene_idx / max(scene_count - 1, 1)
                intensity, emotion = self._project_emotional_state(
                    traits_lower,
                    agent.emotional_pressure,
                    progress,
                    dominant,
                    volatility,
                )

                trigger = self._generate_trigger(
                    emotion,
                    progress,
                    agent.name,
                    world,
                )

                beats_until = max(
                    1,
                    int(scene_count - scene_idx - 1)
                    if scene_idx < scene_count - 1
                    else 1,
                )

                beat = EmotionalBeat(
                    character=agent.name,
                    emotion=emotion,
                    intensity=intensity,
                    trigger=trigger,
                    beats_until_resolution=beats_until,
                )
                beats.append(beat)

            resolution = _EMOTION_RESOLUTION.get(dominant, "unresolved")

            arc = EmotionalArc(
                character=agent.name,
                beats=beats,
                dominant_emotion=dominant,
                volatility=volatility,
                resolution_state=resolution,
            )
            arcs.append(arc)

        return arcs

    def _dominant_emotion(self, traits: list[str]) -> str:
        for trait in traits:
            if trait in _TRAIT_EMOTION_MAP:
                return _TRAIT_EMOTION_MAP[trait]
        return "neutral"

    def _compute_volatility(self, traits: list[str]) -> float:
        if not traits:
            return 0.3
        scores = [_TRAIT_VOLATILITY.get(t, 0.3) for t in traits]
        return mean(scores)

    def _project_emotional_state(
        self,
        traits: list[str],
        base_pressure: float,
        progress: float,
        dominant: str,
        volatility: float,
    ) -> tuple[float, str]:
        """Project emotional intensity and state at a given story progress point.

        Early story: intensity rises from base_pressure
        Mid story: peaks near progress 0.5-0.7
        Late story: resolves toward lower intensity
        """
        # Arc-shaped intensity: rise, peak, fall
        if progress < 0.3:
            intensity = base_pressure + (progress / 0.3) * 0.3
        elif progress < 0.7:
            peak = (progress - 0.3) / 0.4
            intensity = base_pressure + 0.3 + peak * 0.4
        else:
            resolution = (progress - 0.7) / 0.3
            intensity = base_pressure + 0.7 - resolution * 0.6

        intensity = max(0.0, min(1.0, intensity))

        # Determine emotion at this progress point
        if progress > 0.85:
            if dominant in ("anger", "fear", "desperation", "jealousy"):
                # Transform negative emotions toward resolution
                if dominant == "anger":
                    emotion = "sadness"
                elif dominant == "fear":
                    emotion = "hope"
                elif dominant == "desperation":
                    emotion = "hope"
                elif dominant == "jealousy":
                    emotion = "sadness"
                else:
                    emotion = "neutral"
            else:
                emotion = dominant
        elif progress > 0.5 and volatility > 0.6:
            # High-volatility characters may shift mid-story
            possible = ["anger", "fear", "desperation", "guilt"]
            emotion = possible[int((progress * 10) % len(possible))]
        else:
            emotion = dominant

        return intensity, emotion

    def _generate_trigger(
        self,
        emotion: str,
        progress: float,
        character: str,
        world: WorldConstraints,
    ) -> str:
        """Generate a plausible trigger for the emotional state."""
        conflicts = world.active_conflicts

        if emotion == "anger":
            if conflicts:
                return f"{character} confronts {conflicts[0].lower()}"
            return f"{character} faces an obstacle"
        elif emotion == "fear":
            if world.unresolved_mysteries:
                return f"{character} fears {world.unresolved_mysteries[0].lower()}"
            return f"{character} senses approaching danger"
        elif emotion == "joy":
            return f"{character} finds unexpected support"
        elif emotion == "sadness":
            if progress > 0.5:
                return f"{character} mourns what was lost"
            return f"{character} reflects on past regrets"
        elif emotion == "guilt":
            return f"{character} remembers a past failure"
        elif emotion == "shame":
            return f"{character}'s weakness is exposed"
        elif emotion == "jealousy":
            return f"{character} sees another succeed where they failed"
        elif emotion == "hope":
            if progress > 0.7:
                return f"{character} sees a path forward"
            return f"{character} believes change is possible"
        elif emotion == "desperation":
            return f"{character} faces impossible odds"
        return f"{character} processes the events unfolding"


# ---------------------------------------------------------------------------
# EmotionalSpecValidator — validates emotional arcs for coherence
# ---------------------------------------------------------------------------


class EmotionalSpecValidator:
    """Validates emotional arcs for coherence, completeness, and quality."""

    def validate(self, arcs: list[EmotionalArc]) -> list[str]:
        """Return validation warnings for emotional arcs."""
        warnings: list[str] = []

        for arc in arcs:
            # Check for empty arcs
            if not arc.beats:
                warnings.append(f"{arc.character}: No emotional beats defined")

            # Check volatility range
            if arc.volatility < 0.0 or arc.volatility > 1.0:
                warnings.append(
                    f"{arc.character}: Volatility {arc.volatility:.2f} out of range [0,1]"
                )

            # Check for intensity cliff (sudden drop from >0.8 to <0.2)
            for i in range(1, len(arc.beats)):
                prev = arc.beats[i - 1]
                curr = arc.beats[i]
                if prev.intensity > 0.8 and curr.intensity < 0.2:
                    warnings.append(
                        f"{arc.character}: Intensity cliff between beat {i-1}->{i} "
                        f"({prev.intensity:.2f} -> {curr.intensity:.2f})"
                    )

            # Check beats_until_resolution consistency
            for i, beat in enumerate(arc.beats):
                if beat.beats_until_resolution < 0:
                    warnings.append(
                        f"{arc.character}: Negative beats_until_resolution at beat {i}"
                )

        return warnings

    def arc_coherence(self, arcs: list[EmotionalArc]) -> float:
        """Compute a coherence score for emotional arcs (0-1)."""
        if not arcs:
            return 1.0

        scores: list[float] = []

        for arc in arcs:
            if len(arc.beats) < 2:
                scores.append(0.5)
                continue

            # 1. Intensity should follow a hill shape (low → high → low)
            intensities = [b.intensity for b in arc.beats]
            mid = len(intensities) // 2
            left_rising = all(
                intensities[i] <= intensities[i + 1]
                for i in range(mid - 1)
            ) if mid > 1 else True
            right_falling = all(
                intensities[i] >= intensities[i + 1]
                for i in range(mid, len(intensities) - 1)
            ) if len(intensities) - mid > 1 else True
            hill_score = 1.0 if (left_rising and right_falling) else (
                0.5 if (left_rising or right_falling) else 0.0
            )
            scores.append(hill_score)

            # 2. Resolution state should match final intensity
            final_intensity = intensities[-1]
            if arc.resolution_state == "resolved" and final_intensity > 0.5:
                scores.append(0.3)
            elif arc.resolution_state == "unresolved" and final_intensity < 0.2:
                scores.append(0.3)
            else:
                scores.append(1.0)

            # 3. Volatility shouldn't cause erratic emotion shifts
            emotion_changes = sum(
                1 for i in range(1, len(arc.beats))
                if arc.beats[i].emotion != arc.beats[i - 1].emotion
            )
            expected_changes = max(1, int(arc.volatility * len(arc.beats) * 0.5))
            change_diff = abs(emotion_changes - expected_changes) / max(len(arc.beats), 1)
            change_score = max(0.0, 1.0 - change_diff)
            scores.append(change_score)

        return mean(scores) if scores else 1.0


# ---------------------------------------------------------------------------
# EmotionalSpecIntegrator — integrates emotional arcs into scene blueprints
# ---------------------------------------------------------------------------


class EmotionalSpecIntegrator:
    """Integrates emotional arcs into scene blueprints for generation."""

    def integrate(
        self,
        arcs: list[EmotionalArc],
        blueprint: SceneBlueprint,
        scene_index: int,
    ) -> SceneBlueprint:
        """Modify scene blueprint based on emotional arcs at current scene index."""
        objective = blueprint.objective
        agent_states = dict(blueprint.agent_states)

        # Adjust required_tension based on dominant emotional intensity at this beat
        max_intensity = 0.0
        emotional_context: dict[str, str] = {}

        for arc in arcs:
            if scene_index < len(arc.beats):
                beat = arc.beats[scene_index]
                if beat.intensity > max_intensity:
                    max_intensity = beat.intensity
                emotional_context[arc.character] = beat.emotion

                # Apply emotional pressure to agent state
                if arc.character in agent_states:
                    agent = agent_states[arc.character]
                    agent.emotional_pressure = max(
                        agent.emotional_pressure,
                        beat.intensity * 0.5,
                    )

        # Blend emotional intensity into required_tension
        blended_tension = max(
            objective.required_tension,
            max_intensity * 0.4,
        )
        blended_tension = min(1.0, blended_tension)

        # Add emotional context to purpose
        if emotional_context:
            emotion_desc = "; ".join(
                f"{char} feels {emotion}"
                for char, emotion in emotional_context.items()
            )
            purpose = f"{objective.purpose} [{emotion_desc}]"
        else:
            purpose = objective.purpose

        new_objective = SceneObjective(
            purpose=purpose,
            characters_involved=objective.characters_involved,
            location=objective.location,
            conflict_type=objective.conflict_type,
            required_tension=blended_tension,
            target_scene_type=objective.target_scene_type,
            resolution_goal=objective.resolution_goal,
        )

        return SceneBlueprint(
            objective=new_objective,
            agent_states=agent_states,
            world=blueprint.world,
            retrieved_memories=blueprint.retrieved_memories,
        )

from __future__ import annotations

import json
import random

from backend.v2.rag_bridge import RAGBridge
from backend.v2.types import (
    ArcPhase,
    SceneObjective,
    SceneType,
    StoryMode,
    WorldConstraints,
)


class StoryPlanner:
    """Produces SceneObjectives that drive scene generation.

    Outputs must specify scene purpose, tension progression, pacing,
    revelations, and payoffs — not generic commentary.
    """

    def __init__(
        self,
        rag_bridge: RAGBridge | None = None,
        blueprints_path: str | None = None,
    ) -> None:
        self._chapter_count = 0
        self._tension_curve: list[float] = []
        self._blueprints: list[dict] = []
        self.rag_bridge = rag_bridge
        if rag_bridge is not None and rag_bridge.is_loaded:
            self._seed_from_rag_bridge()
        elif blueprints_path is not None:
            self._load_blueprints(blueprints_path)

    def _seed_from_rag_bridge(self) -> None:
        """Load scene blueprints via RAGBridge."""
        if self.rag_bridge is None:
            return
        raw = self.rag_bridge.retrieve_blueprints()
        self._blueprints = raw

    def _load_blueprints(self, path: str) -> None:
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    self._blueprints.append(json.loads(line))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def plan_chapter(
        self,
        chapter_num: int,
        total_chapters: int,
        world: WorldConstraints,
        story_mode: StoryMode,
        character_count: int = 0,
    ) -> list[SceneObjective]:
        scenes: list[SceneObjective] = []
        progress = chapter_num / max(total_chapters, 1)

        phase = self._determine_chapter_phase(progress, story_mode)

        scene_types = self._select_scene_types(phase, story_mode, character_count)
        tensions = self._tension_for_scenes(len(scene_types), phase)

        for i, (stype, tension) in enumerate(zip(scene_types, tensions)):
            purpose = self._purpose_for_scene(stype, phase, i, len(scene_types))
            obj = SceneObjective(
                purpose=purpose,
                characters_involved=[],
                location=world.location_description or "",
                conflict_type=self._conflict_for_phase(phase),
                required_tension=tension,
                target_scene_type=stype,
                resolution_goal=self._resolution_goal(stype, phase),
            )
            scenes.append(obj)

        return scenes

    def _determine_chapter_phase(
        self, progress: float, story_mode: StoryMode
    ) -> ArcPhase:
        if story_mode == StoryMode.SHORT:
            return ArcPhase.RISING
        if progress < 0.2:
            return ArcPhase.CALM
        if progress < 0.4:
            return ArcPhase.RISING
        if progress < 0.7:
            return ArcPhase.PEAK
        if progress < 0.9:
            return ArcPhase.FALLING
        return ArcPhase.RESOLUTION

    def _select_scene_types(self, phase: ArcPhase, mode: StoryMode, character_count: int = 0) -> list[SceneType]:
        pool = {
            ArcPhase.CALM: [SceneType.DESCRIPTION, SceneType.INTROSPECTION, SceneType.DIALOGUE],
            ArcPhase.RISING: [SceneType.DIALOGUE, SceneType.ACTION, SceneType.TRANSITION],
            ArcPhase.PEAK: [SceneType.ACTION, SceneType.DIALOGUE, SceneType.INTROSPECTION],
            ArcPhase.FALLING: [SceneType.INTROSPECTION, SceneType.DIALOGUE, SceneType.TRANSITION],
            ArcPhase.RESOLUTION: [SceneType.DESCRIPTION, SceneType.INTROSPECTION, SceneType.DIALOGUE],
        }
        candidates = list(pool.get(phase, pool[ArcPhase.CALM]))
        count = 3 if mode == StoryMode.SHORT else random.randint(3, 5)

        # Occasionally use blueprint conflicts to influence scene selection
        if self._blueprints and random.random() < 0.3:
            bp = random.choice(self._blueprints)
            bp_patterns = bp.get("reusable_patterns", [])
            for pat in bp_patterns:
                if "conflict:" in pat:
                    if "rising" in pat or "interpersonal" in pat:
                        candidates = [SceneType.ACTION, SceneType.DIALOGUE, SceneType.TRANSITION]
                        break
                    if "climax" in pat:
                        candidates = [SceneType.ACTION, SceneType.INTROSPECTION]
                        break

        result: list[SceneType] = [random.choice(candidates) for _ in range(count)]

        # Ensure at least one DIALOGUE scene for SHORT mode with 2+ characters.
        # This fixes the issue where dialogue scenes never fire because random
        # selection produces no DIALOGUE (about 30% probability with 3 picks from
        # a 3-element pool).
        if mode == StoryMode.SHORT and character_count >= 2 and SceneType.DIALOGUE not in result:
            idx = random.randint(0, count - 1)
            result[idx] = SceneType.DIALOGUE

        return result

    def _tension_for_scenes(
        self, scene_count: int, phase: ArcPhase
    ) -> list[float]:
        base = {
            ArcPhase.CALM: 0.2,
            ArcPhase.RISING: 0.4,
            ArcPhase.PEAK: 0.8,
            ArcPhase.FALLING: 0.5,
            ArcPhase.RESOLUTION: 0.2,
        }.get(phase, 0.5)

        # Occasionally borrow tension curve shape from blueprints
        if self._blueprints and random.random() < 0.3:
            bp = random.choice(self._blueprints)
            bp_curve = bp.get("tension_curve", [])
            if len(bp_curve) >= scene_count:
                return [min(1.0, max(0.0, v)) for v in bp_curve[:scene_count]]

        return [min(1.0, base + (i / scene_count) * 0.3) for i in range(scene_count)]

    def _purpose_for_scene(
        self, stype: SceneType, phase: ArcPhase, index: int, total: int
    ) -> str:
        purposes = {
            SceneType.ACTION: [
                "character confronts an obstacle",
                "physical conflict erupts",
                "chase or escape sequence",
                "discovery through action",
                "desperate struggle ensues",
                "ambush or sudden attack",
            ],
            SceneType.DIALOGUE: [
                "character reveals crucial information",
                "negotiation between parties",
                "confession or betrayal exposed",
                "alliance formed or broken",
                "secret bargain struck",
                "accusation and denial",
            ],
            SceneType.INTROSPECTION: [
                "character reflects on past events",
                "inner conflict surfaces",
                "decision point reached",
                "emotional turning point",
                "memory reshapes understanding",
                "moment of doubt or resolve",
            ],
            SceneType.DESCRIPTION: [
                "environment establishes mood",
                "world detail foreshadows danger",
                "atmosphere builds tension",
                "setting reveals history",
                "weather mirrors emotion",
                "decay or grandeur observed",
            ],
            SceneType.TRANSITION: [
                "passage of time shown",
                "location change with consequence",
                "montage of preparations",
                "journey with reflection",
                "interruption changes course",
                "news arrives from afar",
            ],
        }
        pool = list(purposes.get(stype, ["scene advances the narrative"]))

        # Blueprint-inspired purposes for extra variety
        if self._blueprints and random.random() < 0.25:
            bp = random.choice(self._blueprints)
            rev = bp.get("revelation_pattern", "")
            cli = bp.get("climax_pattern", "")
            if rev == "discovery_revelation" and stype == SceneType.DIALOGUE:
                pool.append("truth revealed through confrontation")
            if cli == "emotional_climax" and stype == SceneType.INTROSPECTION:
                pool.append("emotional breakthrough or breakdown")
            if cli == "combat_climax" and stype == SceneType.ACTION:
                pool.append("life-or-death struggle decided")

        return random.choice(pool)

    def _conflict_for_phase(self, phase: ArcPhase) -> str:
        # Blueprint-inspired conflict labels
        if self._blueprints and random.random() < 0.3:
            bp = random.choice(self._blueprints)
            bp_conflict = bp.get("conflict_pattern", "")
            if bp_conflict:
                return bp_conflict
        return {
            ArcPhase.CALM: "dormant",
            ArcPhase.RISING: "emerging",
            ArcPhase.PEAK: "explosive",
            ArcPhase.FALLING: "waning",
            ArcPhase.RESOLUTION: "resolved",
        }.get(phase, "neutral")

    def _resolution_goal(self, stype: SceneType, phase: ArcPhase) -> str:
        if phase == ArcPhase.RESOLUTION:
            return "provide closure"
        if stype == SceneType.ACTION:
            return "escalate stakes"
        if stype == SceneType.DIALOGUE:
            return "reveal information"
        if stype == SceneType.INTROSPECTION:
            return "deepen character"
        return "advance the plot"

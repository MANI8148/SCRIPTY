from __future__ import annotations

import re
from enum import Enum
from typing import Any


class ScenePurpose(Enum):
    advance_plot = "advance_plot"
    reveal_character = "reveal_character"
    increase_tension = "increase_tension"
    resolve_conflict = "resolve_conflict"
    provide_information = "provide_information"


class ScenePurposeValidator:
    KEYWORDS: dict[ScenePurpose, set[str]] = {
        ScenePurpose.advance_plot: {"then", "next", "decided", "moved", "found", "began", "continued"},
        ScenePurpose.reveal_character: {"felt", "remembered", "wanted", "feared", "believed", "realized"},
        ScenePurpose.increase_tension: {"danger", "threat", "risk", "conflict", "trap", "pursued", "stakes"},
        ScenePurpose.resolve_conflict: {"resolved", "ended", "settled", "safe", "peace", "defeated", "concluded"},
        ScenePurpose.provide_information: {"truth", "clue", "learned", "revealed", "information", "discovered"},
    }

    def detect_purposes(self, scene_content: str, context: dict | None = None) -> set[ScenePurpose]:
        words = set(re.findall(r"[a-zA-Z']+", scene_content.lower()))
        purposes = {purpose for purpose, keys in self.KEYWORDS.items() if words & keys}
        context = context or {}
        scene_type = str(context.get("scene_type", "")).lower()
        if scene_type == "action":
            purposes.add(ScenePurpose.increase_tension)
            purposes.add(ScenePurpose.advance_plot)
        elif scene_type == "dialogue":
            purposes.add(ScenePurpose.provide_information)
        elif scene_type == "introspection":
            purposes.add(ScenePurpose.reveal_character)
        return purposes

    def validate_scene(self, scene: Any) -> set[ScenePurpose]:
        scene_type = getattr(getattr(scene, "scene_type", ""), "value", getattr(scene, "scene_type", ""))
        return self.detect_purposes(getattr(scene, "content", str(scene)), {"scene_type": scene_type})

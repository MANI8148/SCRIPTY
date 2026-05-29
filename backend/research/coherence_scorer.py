from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CoherenceResult:
    scores: dict[str, float]
    violations: dict[str, list[str]] = field(default_factory=dict)

    @property
    def overall(self) -> float:
        return round(sum(self.scores.values()) / max(1, len(self.scores)), 6)


class CharacterConsistencyChecker:
    def check(self, scenes: list[str], registered_names: set[str]) -> tuple[float, list[str]]:
        if not scenes or not registered_names:
            return 1.0, []
        violations = []
        for index, scene in enumerate(scenes, 1):
            names = set(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", scene))
            unknown = {name for name in names if " " in name and name not in registered_names}
            if unknown:
                violations.append(f"scene {index}: unknown names {sorted(unknown)}")
        return 1.0 - min(1.0, len(violations) / len(scenes)), violations


class EmotionalConsistencyChecker:
    OPPOSITES = {("joyful", "desperate"), ("hopeful", "hopeless"), ("calm", "angry")}

    def check(self, states: list[Any]) -> tuple[float, list[str]]:
        violations = []
        previous = None
        for state in states:
            emotion = getattr(state, "primary_emotion", None) or state.get("primary_emotion", None)
            trigger = getattr(state, "trigger", None) or state.get("trigger", "")
            if previous and (previous, emotion) in self.OPPOSITES and not trigger:
                violations.append(f"unjustified emotional jump: {previous} to {emotion}")
            previous = emotion
        return 1.0 - min(1.0, len(violations) / max(1, len(states))), violations


class CausalConsistencyChecker:
    def check(self, scenes: list[str]) -> tuple[float, list[str]]:
        violations = []
        for index, scene in enumerate(scenes, 1):
            lowered = scene.lower()
            if any(word in lowered for word in ("therefore", "because", "so ")) and not re.search(
                r"\b(because|after|therefore|so|caused)\b", lowered
            ):
                violations.append(f"scene {index}: weak causal link")
        return 1.0 - min(1.0, len(violations) / max(1, len(scenes))), violations


class NarrativeContinuityChecker:
    def check(self, events: list[Any]) -> tuple[float, list[str]]:
        violations = []
        previous = -1
        for event in events:
            chapter = getattr(event, "chapter_num", None) or event.get("chapter_num", 0)
            if chapter < previous:
                violations.append(f"event chapter {chapter} follows {previous}")
            previous = chapter
        return 1.0 if not violations else 0.0, violations


class CoherenceScorer:
    def __init__(self) -> None:
        self.character = CharacterConsistencyChecker()
        self.emotional = EmotionalConsistencyChecker()
        self.causal = CausalConsistencyChecker()
        self.continuity = NarrativeContinuityChecker()

    def score(
        self,
        scenes: list[str],
        *,
        registered_names: set[str] | None = None,
        emotional_states: list[Any] | None = None,
        timeline_events: list[Any] | None = None,
    ) -> CoherenceResult:
        registered_names = registered_names or set()
        emotional_states = emotional_states or []
        timeline_events = timeline_events or []
        scores: dict[str, float] = {}
        violations: dict[str, list[str]] = {}
        for name, result in {
            "character": self.character.check(scenes, registered_names),
            "emotional": self.emotional.check(emotional_states),
            "causal": self.causal.check(scenes),
            "continuity": self.continuity.check(timeline_events),
        }.items():
            scores[name], violations[name] = result
        return CoherenceResult(scores=scores, violations=violations)

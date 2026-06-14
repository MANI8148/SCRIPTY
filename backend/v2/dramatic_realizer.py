"""DramaticRealizer — delegates text generation to HybridGenerator.

When a TextGenerator is available (hybrid mode), realize() delegates
directly to generator.generate(blueprint). When no generator is set
(template fallback mode), produces a simple structured scene.

Kept from legacy:
  - EventKind / DramaticEvent / NarrativeMode (structural types)
  - ParagraphComposer (structural paragraph assembly)
  - Character helpers (_resolve_pronoun, _apply_pronouns, etc.)
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from backend.v2.character_agent import CharacterAgent
from backend.v2.generators.base import TextGenerator
from backend.v2.generators.repetition_state import RepetitionState
from backend.v2.types import (
    AgentState,
    GeneratedScene,
    MemoryEntry,
    SceneBlueprint,
    SceneType,
)


# ─── Event types ────────────────────────────────────────────────────────────


class EventKind(str, Enum):
    OPENING = "opening"
    ACTION = "action"
    DIALOGUE = "dialogue"
    REACTION = "reaction"
    COMPLICATION = "complication"
    OUTCOME = "outcome"


@dataclass
class DramaticEvent:
    kind: EventKind
    text: str
    participants: list[str] = field(default_factory=list)
    tension: float = 0.5


class NarrativeMode(str, Enum):
    CONFRONTATION = "confrontation"
    REVELATION = "revelation"
    BETRAYAL = "betrayal"
    ROMANCE = "romance"
    NEGOTIATION = "negotiation"
    DISCOVERY = "discovery"
    LOSS = "loss"
    TRIUMPH = "triumph"
    MYSTERY = "mystery"
    RECONCILIATION = "reconciliation"
    GENERIC = "generic"


# ─── DramaticRealizer — orchestrator ────────────────────────────────────────


class DramaticRealizer:
    """Transforms SceneBlueprint into dramatic scenes.

    Primary mode: delegates to TextGenerator (HybridGenerator) for
    n-gram-based generation. Falls back to template-mode placeholder
    when no generator is set.
    """

    def __init__(self, generator: TextGenerator | None = None) -> None:
        self._agents_map: dict[str, CharacterAgent] = {}
        self._rep_state: RepetitionState = RepetitionState()
        self._current_mode: NarrativeMode = NarrativeMode.GENERIC
        self._generator: TextGenerator | None = generator

    def set_generator(self, generator: TextGenerator) -> None:
        """Set the TextGenerator for hybrid mode generation."""
        self._generator = generator

    def set_agents(self, agents: list[CharacterAgent]) -> None:
        """Register CharacterAgents for voice-aware dialogue generation."""
        self._agents_map = {a.name: a for a in agents}
        if self._generator is not None and hasattr(self._generator, "set_agents"):
            self._generator.set_agents(agents)

    def perceive_scene(self, scene: GeneratedScene) -> None:
        for agent in self._agents_map.values():
            if agent.name in scene.characters_involved:
                entry = MemoryEntry(
                    text=scene.content,
                    source="generated",
                    chapter_num=0,
                    scene_num=0,
                    characters=scene.characters_involved,
                    relevance_score=0.5,
                )
                agent.perceive(entry)

    def realize(self, blueprint: SceneBlueprint) -> GeneratedScene:
        if self._generator is not None:
            return self._generator.generate(blueprint)
        return self._template_fallback(blueprint)

    def _template_fallback(self, blueprint: SceneBlueprint) -> GeneratedScene:
        """Minimal template fallback when no generator is set."""
        obj = blueprint.objective
        chars = ", ".join(obj.characters_involved) if obj.characters_involved else "unknown"
        content = (
            f"[{obj.target_scene_type.value.upper()} SCENE]\n"
            f"{obj.purpose.capitalize()} involving {chars} "
            f"at {obj.location}."
        )
        return GeneratedScene(
            content=content,
            scene_type=obj.target_scene_type,
            word_count=len(content.split()),
            tension=obj.required_tension,
            characters_involved=obj.characters_involved,
        )

    def report(self) -> dict[str, int]:
        """Return RepetitionState usage report for instrumentation."""
        return self._rep_state.stats()

    # ── Text helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _strip_trailing_punc(text: str) -> str:
        return text.rstrip(",.!?;:\u201c\u201d\u2018\u2019")

    @staticmethod
    def _sanitize_fragment(text: str) -> str:
        text = re.sub(r"\['.*?'\]", "", text)
        text = re.sub(
            r"\b([A-Za-z])\s+(?=stirred|flickered|lingered|warmed|pulled|tightened|"
            r"echoed|clawed|changed|came|felt|pressed|surfaced|thought)\b",
            "", text,
        )
        text = re.sub(r"\bthe memory of I've\b", "", text)
        text = re.sub(
            r"^(He|She|he|she|His|Her|his|her|There|Here|Then|Now|When|Where|"
            r"Why|How|It|Its|This|That|These|Those)\s+", "", text,
        )
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _resolve_possessive(name: str) -> str:
        female_endings = ("a", "e", "i", "y", "ah", "ia", "na", "ra", "la", "ma", "da")
        for ending in female_endings:
            if name.lower().strip().endswith(ending):
                return "her"
        return "his"

    @staticmethod
    def _resolve_pronoun(name: str, subjective: bool = True) -> str:
        female_endings = ("a", "e", "i", "y", "ah", "ia", "na", "ra", "la", "ma", "da")
        for ending in female_endings:
            if name.lower().strip().endswith(ending):
                return "she" if subjective else "her"
        return "he" if subjective else "him"

    @staticmethod
    def _apply_pronouns(text: str, name: str) -> str:
        poss = DramaticRealizer._resolve_possessive(name)
        sbj = DramaticRealizer._resolve_pronoun(name)
        obj = DramaticRealizer._resolve_pronoun(name, False)
        is_female = poss == "her"

        def _swap(m: re.Match) -> str:
            w = m.group(0)
            lower = w.lower()
            if not is_female:
                if lower == "she":
                    return "he" if w[0].islower() else "He"
                if lower == "her":
                    return "his" if w[0].islower() else "His"
            else:
                if lower == "he":
                    return "she" if w[0].islower() else "She"
                if lower == "him":
                    return "her" if w[0].islower() else "Her"
                if lower == "his":
                    return "her" if w[0].islower() else "Her"
            return w

        return re.sub(
            r'\b(He|he|Him|him|His|his|She|she|Her|her)\b', _swap, text,
        )

    # ── Dialogue-from-state generator ────────────────────────────────────

    def _generate_dialogue_from_state(
        self,
        agent: AgentState,
        other_name: str,
        bp: SceneBlueprint,
    ) -> str | None:
        intention = agent.intention
        if not intention or not intention.goal:
            return None
        pressure = agent.emotional_pressure
        rel_val = (
            agent.beliefs.relationship_beliefs.get(other_name, "").lower()
            if agent.beliefs else ""
        )
        goal_ref = random.choice([
            "this", "what we are after", "what must be done",
            "what I came for", "the task ahead", "what matters most",
        ])

        if rel_val in ("enemy", "hostile", "distrusted"):
            templates = [
                f"You are in my way. {goal_ref} will not wait.",
                f"I will do what it takes. Even if that means going through you.",
                f"You should have stayed out of this. {goal_ref} is mine.",
                f"Do not pretend you care. We both know where this ends.",
            ]
        elif rel_val in ("ally", "friend", "trusted", "family"):
            templates = [
                f"I need you with me on this. {goal_ref} cannot happen alone.",
                f"Trust me. {goal_ref} is what matters.",
                f"We have come this far together. Do not stop now.",
                f"I know it is hard, but {goal_ref} is the only way forward.",
            ]
        elif pressure > 0.7:
            templates = [
                f"There is no time! {goal_ref} must happen now.",
                f"Every second counts. {goal_ref} before it is too late.",
                f"Do you not see? {goal_ref} is all that stands between us and disaster.",
            ]
        else:
            templates = [
                f"This changes things. {goal_ref} is what we should focus on.",
                f"I have been thinking. {goal_ref} might be the answer.",
                f"There is something you should know. {goal_ref} is not what it seems.",
            ]
        return random.choice(templates)

    # ── Paragraph Composer ───────────────────────────────────────────────

    @staticmethod
    def _compose_paragraphs(events: list[DramaticEvent]) -> str:
        if not events:
            return ""
        involved_names: set[str] = set()
        for e in events:
            involved_names.update(e.participants)
        paragraphs: list[str] = []
        for i, event in enumerate(events):
            text = event.text
            if i > 0 and involved_names:
                has_name = any(n in text for n in involved_names)
                if not has_name and event.participants:
                    candidates = [p for p in event.participants if p in involved_names]
                    if candidates:
                        name = random.choice(candidates)
                        if event.kind == EventKind.REACTION:
                            text = f"{name} felt the weight of it. {text}"
                        elif event.kind == EventKind.OUTCOME:
                            text = f"For {name}, {text[0].lower()}{text[1:]}" if text else text
                        elif event.kind == EventKind.COMPLICATION:
                            text = f"{name} saw it coming. {text[0].lower()}{text[1:]}" if text else text
                        else:
                            text = f"{name} {text[0].lower()}{text[1:]}" if text else text
            if i > 0 and event.kind == EventKind.DIALOGUE and not text.startswith("\n\n"):
                text = f"\n\n{text}"
            paragraphs.append(text)
        return "\n\n".join(paragraphs)

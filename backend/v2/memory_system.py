"""
SCRIPTY v2 — MemorySystem
Multi-tier memory with lazy loading by generation mode.
"""
from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from backend.v2.types import (
    CharacterBeliefs,
    MemoryEntry, MemoryBundle, MemoryQuery, SceneBlueprint, AgentState, CharacterRecord
)


class ConsequenceEngine:
    """Tracks action success rates per character."""
    def __init__(self):
        self._attempts: dict[str, list[bool]] = {}

    def record(self, character: str, success: bool):
        self._attempts.setdefault(character, []).append(success)

    def success_rate(self, character: str) -> float:
        attempts = self._attempts.get(character, [])
        if not attempts:
            return 0.5
        return sum(attempts) / len(attempts)


@dataclass
class EpisodicMemory:
    entries: list[MemoryEntry] = field(default_factory=list)
    max_size: int = 1000

    def add(self, entry: MemoryEntry):
        self.entries.append(entry)
        if len(self.entries) > self.max_size:
            self.entries = self.entries[-self.max_size:]

    def recent(self, character: str, window: int = 3) -> list[MemoryEntry]:
        char_entries = [e for e in self.entries if e.character == character]
        return char_entries[-window:]

    def get_by_importance(self, threshold: float = 0.5) -> list[MemoryEntry]:
        return [e for e in self.entries if e.importance >= threshold]


@dataclass
class SemanticMemory:
    facts: dict[str, MemoryEntry] = field(default_factory=dict)

    def add_fact(self, key: str, entry: MemoryEntry):
        self.facts[key] = entry

    def get_fact(self, key: str) -> Optional[MemoryEntry]:
        return self.facts.get(key)

    def all_facts(self) -> list[MemoryEntry]:
        return list(self.facts.values())


@dataclass
class BeliefMemory:
    beliefs: dict[str, dict[str, MemoryEntry]] = field(default_factory=lambda: defaultdict(dict))

    def add_belief(self, character: str, key: str, entry: MemoryEntry):
        self.beliefs[character][key] = entry

    def get_beliefs(self, character: str) -> list[MemoryEntry]:
        return list(self.beliefs.get(character, {}).values())


class MemorySystem:
    """
    Multi-tier memory system with mode-aware lazy loading.
    SHORT: episodic + semantic only
    CHAPTER: + belief
    BOOK: full stack (all 9 subtypes)
    """

    def __init__(self, mode: str = "SHORT"):
        self.mode = mode.upper()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.belief = BeliefMemory()
        self._character_registry: set[str] = set()
        self._character_beliefs: dict[str, CharacterBeliefs] = {}
        self.consequence_engine = ConsequenceEngine()

        self._lazy_subsystems: dict[str, Any] = {}
        self._initialized_subsystems = False

    def register_character(self, name: str):
        self._character_registry.add(name)
        if name not in self._character_beliefs:
            self._character_beliefs[name] = CharacterBeliefs()

    def _init_lazy_subsystems(self):
        if self._initialized_subsystems:
            return
        if self.mode in ("CHAPTER", "BOOK"):
            from backend.v2.memory_interpretation import InterpretationMemory
            from backend.v2.memory_consequence import ConsequenceMemory
            from backend.v2.memory_emotional import EmotionalRetrieval
            from backend.v2.memory_relationship import RelationshipDelta
            from backend.v2.memory_callback import CallbackScheduler
            self._lazy_subsystems = {
                "interpretation": InterpretationMemory(),
                "consequence": ConsequenceMemory(),
                "emotional": EmotionalRetrieval(),
                "relationship": RelationshipDelta(),
                "callback": CallbackScheduler(),
            }
        self._initialized_subsystems = True

    def record_scene(self, blueprint: SceneBlueprint, generated_text: str, agent_states: list[AgentState]):
        for agent in agent_states:
            entry = MemoryEntry(
                character=agent.character.name,
                content=generated_text[:500],
                scene_num=blueprint.scene_num,
                chapter_num=blueprint.chapter_num,
                event_type=blueprint.objective.target_scene_type.value,
                emotional_impact=agent.emotional_pressure,
                importance=min(1.0, 0.3 + agent.emotional_pressure * 0.7),
                metadata={"objective": blueprint.objective.purpose}
            )
            self.episodic.add(entry)

            if self.mode in ("CHAPTER", "BOOK"):
                self._init_lazy_subsystems()
                self._lazy_subsystems["interpretation"].process(agent.character.name, entry)
                self._lazy_subsystems["consequence"].process(agent.character.name, entry)
                self._lazy_subsystems["emotional"].process(agent.character.name, entry)
                self._lazy_subsystems["relationship"].process(agent.character.name, entry)
                self._lazy_subsystems["callback"].schedule(agent.character.name, entry)

    def retrieve(self, blueprint_or_query, **kwargs) -> MemoryBundle | list[MemoryEntry]:
        """Retrieve memories. Accepts SceneBlueprint or MemoryQuery."""
        # Handle MemoryQuery (backward-compatible with tests)
        if isinstance(blueprint_or_query, MemoryQuery):
            query = blueprint_or_query
            results = []
            for entry in self.episodic.entries:
                if entry.character == query.focus_character or query.focus_character in (entry.characters or []):
                    if not query.context_query or query.context_query.lower() in (entry.text + entry.content).lower():
                        results.append(entry)
            return results[-query.top_k:] if results else []

        self._init_lazy_subsystems()
        blueprint = blueprint_or_query

        states = blueprint.agent_states
        if isinstance(states, dict):
            states = list(states.values())
        char_names = [a.character.name for a in states]
        recent = []
        for name in char_names:
            recent.extend(self.episodic.recent(name, window=3))

        bundle = MemoryBundle(
            episodic=recent,
            semantic=self.semantic.all_facts(),
            belief=[],
        )

        for name in char_names:
            bundle.belief.extend(self.belief.get_beliefs(name))

        if self.mode == "BOOK":
            for name in char_names:
                if "interpretation" in self._lazy_subsystems:
                    bundle.interpretation.extend(self._lazy_subsystems["interpretation"].retrieve(name, blueprint))
                if "consequence" in self._lazy_subsystems:
                    bundle.consequence.extend(self._lazy_subsystems["consequence"].retrieve(name, blueprint))
                if "emotional" in self._lazy_subsystems:
                    bundle.emotional.extend(self._lazy_subsystems["emotional"].retrieve(name, blueprint))
                if "relationship" in self._lazy_subsystems:
                    bundle.relationship.extend(self._lazy_subsystems["relationship"].retrieve(name, blueprint))
                if "callback" in self._lazy_subsystems:
                    bundle.callback.extend(self._lazy_subsystems["callback"].retrieve(name, blueprint))

        return bundle

    def recent_context(self, character: str, window: int = 3) -> list[MemoryEntry]:
        return self.episodic.recent(character, window)

    def beliefs_for(self, character: str) -> CharacterBeliefs:
        """Return CharacterBeliefs for the named character."""
        if character not in self._character_beliefs:
            self._character_beliefs[character] = CharacterBeliefs()
        return self._character_beliefs[character]

    def record_fact(self, text: str, chapter_num: int, scene_num: int, characters: list[str]):
        key = f"fact_{chapter_num}_{scene_num}_{characters[0] if characters else 'none'}"
        entry = MemoryEntry(
            text=text,
            content=text,
            chapter_num=chapter_num,
            scene_num=scene_num,
            characters=characters,
            event_type="fact",
        )
        self.semantic.add_fact(key, entry)

    def record_event(self, text: str, chapter_num: int, scene_num: int, characters: list[str], relevance_score: float = 0.5):
        for char in characters:
            entry = MemoryEntry(
                text=text,
                content=text,
                chapter_num=chapter_num,
                scene_num=scene_num,
                characters=characters,
                character=char,
                relevance_score=relevance_score,
                event_type="event",
            )
            self.episodic.add(entry)

    def consequences_for_action(self, action: str) -> list:
        """Query consequences for a given action text."""
        results = []
        for char, entries in self.consequence_engine._attempts.items():
            pass  # We use lazy subsystems below
        self._init_lazy_subsystems()
        if "consequence" in self._lazy_subsystems:
            cons_mem = self._lazy_subsystems["consequence"]
            for char, entries in cons_mem.consequences.items():
                for entry in entries:
                    if action.lower() in (entry.content or "").lower():
                        results.append(entry)
        return results

    def schedule_callback(self, memory_id: str, trigger_chapter: int, callback_data: dict):
        self._init_lazy_subsystems()
        if "callback" in self._lazy_subsystems:
            self._lazy_subsystems["callback"]._schedule(callback_data, trigger_chapter)

    def check_callbacks(self, chapter_num: int) -> list:
        self._init_lazy_subsystems()
        if "callback" in self._lazy_subsystems:
            return self._lazy_subsystems["callback"].check(chapter_num)
        return []

    def mark_callback_fired(self, callback_id: str):
        self._init_lazy_subsystems()
        if "callback" in self._lazy_subsystems:
            self._lazy_subsystems["callback"].mark_fired(callback_id)

    def interpret_event(self, event_text: str, character_name: str, character_traits: list[str], chapter_num: int, scene_num: int):
        self._init_lazy_subsystems()
        if "interpretation" in self._lazy_subsystems:
            entry = MemoryEntry(
                text=event_text,
                content=event_text,
                character=character_name,
                chapter_num=chapter_num,
                scene_num=scene_num,
            )
            self._lazy_subsystems["interpretation"].process(character_name, entry)

    def record_interpretation(
        self,
        character: str,
        source_event: str,
        interpretation: str,
        emotion_impact: str,
        confidence: float,
        chapter_num: int,
        scene_num: int,
    ) -> None:
        """Record an HWSE-derived character interpretation of an event.

        Wired from HWSEPipeline.after_scene(). Delegates to the lazy
        InterpretationMemory subsystem when available (CHAPTER/BOOK modes),
        and always retains a retrievable semantic copy so callers that
        enable HWSE independently of memory mode still mutate state.
        """
        self._init_lazy_subsystems()
        entry = MemoryEntry(
            text=f"{character} interpreted: {interpretation}",
            content=interpretation,
            character=character,
            chapter_num=chapter_num,
            scene_num=scene_num,
            event_type="interpretation",
            relevance_score=float(confidence),
            metadata={
                "source_event": source_event,
                "emotion_impact": emotion_impact,
                "confidence": confidence,
            },
        )
        if "interpretation" in self._lazy_subsystems:
            self._lazy_subsystems["interpretation"].process(character, entry)
        # Always keep a retrievable copy in semantic memory.
        self.semantic.add_fact(f"interp_{chapter_num}_{scene_num}_{character}", entry)

    def record_consequence(self, character: str, action: str, consequence: str, success: bool, impact: float, chapter_num: int, scene_num: int):
        self._init_lazy_subsystems()
        if "consequence" in self._lazy_subsystems:
            entry = MemoryEntry(
                text=consequence,
                content=consequence,
                character=character,
                chapter_num=chapter_num,
                scene_num=scene_num,
            )
            self._lazy_subsystems["consequence"].process(character, entry)

    def record_relationship_delta(self, a: str, b: str, old_rel, new_rel, trigger: str, chapter_num: int):
        self._init_lazy_subsystems()
        if "relationship" in self._lazy_subsystems:
            entry = MemoryEntry(
                text=trigger,
                content=trigger,
                chapter_num=chapter_num,
                characters=[a, b],
            )
            self._lazy_subsystems["relationship"].process(a, entry, new_rel)

    def current_relationship_sentiment(self, a: str, b: str) -> float:
        self._init_lazy_subsystems()
        if "relationship" in self._lazy_subsystems:
            return self._lazy_subsystems["relationship"].sentiment(a, b)
        return 0.0

    def snapshot(self) -> dict[str, int]:
        # Ensure lazy subsystems are initialized so counts reflect reality.
        self._init_lazy_subsystems()

        interpretation_count = 0
        consequence_count = 0
        relationship_delta_count = 0

        interpretation = self._lazy_subsystems.get("interpretation")
        if interpretation is not None:
            interpretation_count = sum(
                len(v) for v in interpretation.interpretations.values()
            )
        consequence = self._lazy_subsystems.get("consequence")
        if consequence is not None:
            consequence_count = sum(
                len(v) for v in consequence.consequences.values()
            )
        relationship = self._lazy_subsystems.get("relationship")
        if relationship is not None:
            relationship_delta_count = sum(
                len(v) for v in relationship.deltas.values()
            )

        return {
            "episodic_count": len(self.episodic.entries),
            "semantic_count": len(self.semantic.facts),
            "belief_count": sum(len(v) for v in self.belief.beliefs.values()),
            "interpretation_count": interpretation_count,
            "consequence_count": consequence_count,
            "relationship_delta_count": relationship_delta_count,
        }
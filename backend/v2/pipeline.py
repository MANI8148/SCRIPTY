from __future__ import annotations

import random
from typing import Any

from backend.v2.character_agent import CharacterAgent
from backend.v2.conflict_resolver import ConflictResolver
from backend.v2.dramatic_realizer import DramaticRealizer
from backend.v2.generators.base import TextGenerator
from backend.v2.memory_system import MemorySystem
from backend.v2.narrative_retriever import NarrativeRetriever
from backend.v2.config import HWSEMode
from backend.v2.types import (
    GeneratedScene,
    InterpretationEntry,
    MemoryEntry,
    MemoryQuery,
    SceneBlueprint,
    SceneObjective,
    SceneType,
    StoryMode,
    WorldConstraints,
)


class ScenePipeline:
    """Orchestrates all subsystems to produce a single scene.

    Every subsystem has a measurable path to the generated text.
    No output is produced without input from at least one subsystem.

    When enable_hwse=True, the HWSE (Human-Synthetic Story Engine)
    passes run before and after scene generation:
      - before_scene: EmotionalSpec + MomentumExtraction
      - after_scene:  CharacterListening + InterrogationPass + RevisionPass
    """

    def __init__(
        self,
        conflict_resolver: ConflictResolver,
        realizer: DramaticRealizer,
        memory: MemorySystem,
        generator: TextGenerator | None = None,
        narrative_retriever: NarrativeRetriever | None = None,
        enable_hwse: bool = True,
        hwse_pipeline: Any | None = None,
        hwse_mode: HWSEMode = HWSEMode.OFF,
    ) -> None:
        self.conflict_resolver = conflict_resolver
        self.realizer = realizer
        self.memory = memory
        self.generator = generator
        self.narrative_retriever = narrative_retriever
        self.enable_hwse = enable_hwse
        self._hwse = hwse_pipeline
        self._hwse_mode = hwse_mode
        self._agents: list[CharacterAgent] = []

    def set_agents(self, agents: list[CharacterAgent]) -> None:
        """Register agents for voice-aware dialogue generation."""
        self._agents = agents
        self.realizer.set_agents(agents)
        if self.generator is not None:
            self.realizer.set_generator(self.generator)

    def run(
        self,
        agents: list[CharacterAgent],
        world: WorldConstraints,
        chapter_num: int,
        scene_index: int,
        total_scenes: int,
        objective: SceneObjective,
        story_mode: StoryMode = StoryMode.CHAPTER,
    ) -> GeneratedScene:
        # 1. Character agents decide intentions
        world_context = {
            "era": world.era,
            "tech_level": world.tech_level,
            "tone": world.tone,
        }
        for agent in agents:
            memories = self.memory.recent_context(agent.name)
            pressures = {}
            for other in (a.name for a in agents if a.name != agent.name):
                base_pressure = agent.relationship_pressure_with(other)
                sentiment = self.memory.current_relationship_sentiment(agent.name, other)
                if sentiment != 0.0:
                    base_pressure = base_pressure + sentiment * 0.2
                pressures[other] = base_pressure
            agent.decide_intention(world_context, memories, pressures)

        # 2. Snapshot agent states once — used by both resolver and blueprint
        agent_state_map = {a.character.name: a.to_agent_state() for a in agents}
        agent_state_list = list(agent_state_map.values())

        # 3. ConflictResolver arbitrates into refined SceneObjective
        objective = self.conflict_resolver.resolve(agent_state_list, objective)
        resolved_scene_type = self.conflict_resolver.calculate_scene_type(
            agent_state_list, objective.target_scene_type
        )
        if resolved_scene_type != objective.target_scene_type:
            objective = SceneObjective(
                purpose=objective.purpose,
                characters_involved=objective.characters_involved,
                location=objective.location,
                conflict_type=objective.conflict_type,
                required_tension=objective.required_tension,
                target_scene_type=resolved_scene_type,
                resolution_goal=objective.resolution_goal,
            )

        # 4. Memory retrieval — gather episodic memories for each agent
        retrieved: list[MemoryEntry] = []
        for agent in agents:
            bundle = self.memory.retrieve(
                SceneBlueprint(objective=objective, agent_states=agent_state_list)
            )
            retrieved.extend(bundle.episodic)

        # Inject callback memories
        callback_injected: set[str] = set()
        for agent in agents:
            pending = self.memory.check_callbacks(chapter_num)
            for cb in pending:
                cb_id = getattr(cb, '_id', '') or cb.callback_data.get("_callback_id", "")
                if cb_id and cb_id not in callback_injected:
                    chars = cb.callback_data.get("characters", [agent.name])
                    if agent.name in chars:
                        retrieved.append(MemoryEntry(
                            content=cb.callback_data.get(
                                "resurface_text",
                                "A past memory resurfaced with renewed clarity."
                            ),
                            text=cb.callback_data.get(
                                "resurface_text",
                                "A past memory resurfaced with renewed clarity."
                            ),
                            source="callback",
                            chapter_num=chapter_num,
                            scene_num=scene_index,
                            characters=[agent.name],
                            relevance_score=0.8,
                        ))
                        callback_injected.add(cb_id)
                        self.memory.mark_callback_fired(cb_id)

        # B4: Retrieve by emotional tone from episodic store
        emotional_memories = []
        for agent in agents:
            emotion = agent.emotional_state_str()
            if emotion not in ('neutral', None):
                for entry in self.memory.episodic.entries:
                    if entry.emotion_tags and emotion in entry.emotion_tags:
                        emotional_memories.append(entry)

        seen_texts = set(m.text or m.content for m in retrieved)
        for em in emotional_memories:
            key = em.text or em.content
            if key and key not in seen_texts:
                retrieved.append(em)
                seen_texts.add(key)

        # 5. Build SceneBlueprint
        blueprint = SceneBlueprint(
            objective=objective,
            agent_states=agent_state_map,
            world=world,
            retrieved_memories=retrieved,
            scene_type=resolved_scene_type,
        )

        # 5b. NarrativeRetriever classifies memories into structured package
        if self.narrative_retriever is not None:
            blueprint.narrative_package = self.narrative_retriever.retrieve(
                objective, world, retrieved
            )

        # ── HWSE before_scene: EmotionalSpec + Momentum extraction ──────────
        # Optimizes/enriches the blueprint with emotional arcs and pacing.
        # Guarded so default (HWSE-disabled) generation is unaffected.
        if self.enable_hwse and self._hwse is not None:
            blueprint = self._hwse.before_scene(
                agents=agents,
                world=world,
                memory=self.memory,
                scene_history=self._get_scene_history(),
                scene_index=scene_index,
                total_scenes=total_scenes,
                base_blueprint=blueprint,
            )

        # 6. DramaticRealizer produces text
        scene = self.realizer.realize(blueprint)
        self.realizer.perceive_scene(scene)

        # ── HWSE after_scene: Listening + Interrogation + Revision ─────────
        # Mutates agent beliefs / memory via the HWSE passes AND may return a
        # revised scene (high-priority revisions applied). Capture and return
        # the revised text so the improvements actually reach the output.
        if self.enable_hwse and self._hwse is not None:
            hwse_result = self._hwse.after_scene(
                scene=scene,
                agents=agents,
                world=world,
                memory=self.memory,
                scene_history=self._get_scene_history(),
                chapter_num=chapter_num,
                scene_num=scene_index,
            )
            if hwse_result and hwse_result.get("revised_scene") is not None:
                revised = hwse_result["revised_scene"]
                if getattr(revised, "content", ""):
                    scene = revised
                    self.realizer.perceive_scene(scene)

        return scene

    def _get_scene_history(self) -> list[GeneratedScene]:
        """Get the current scene history from HWSE state if available."""
        if self._hwse is not None:
            return self._hwse.state.scene_history
        return []

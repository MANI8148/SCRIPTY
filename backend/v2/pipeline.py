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
            "active_conflicts": world.active_conflicts,
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

        # 4. Memory retrieval from episodic store
        # In SHORT mode, story_mode='short' ensures no chapter filter is
        # applied during retrieval. All events are stored with chapter_num=1
        # and retrieved without chapter filtering.
        retrieved: list[MemoryEntry] = []
        for agent in agents:
            query = MemoryQuery(
                focus_character=agent.name,
                context_query=objective.purpose,
                top_k=5,
                emotion_filter=agent.emotional_state_str(),
            )
            retrieved.extend(self.memory.retrieve(query, story_mode=story_mode.value if story_mode else None))

        # C4: Direct memory injection for SHORT mode — seed with RAG/corpus
        # when no episodic memories exist yet (first scene of a fresh story).
        if story_mode == StoryMode.SHORT and not retrieved and scene_index == 0:
            from backend.v2.rag_bridge import RAGBridge
            rag = RAGBridge()
            rag.load()
            seed_entries = rag.retrieve(
                MemoryQuery(
                    focus_character=agents[0].name if agents else "protagonist",
                    context_query=objective.purpose,
                    top_k=3,
                )
            )
            for entry in seed_entries:
                entry.chapter_num = chapter_num
                entry.scene_num = scene_index
            retrieved.extend(seed_entries)

        # Inject callback memories (Change 3)
        callback_injected: set[str] = set()
        for agent in agents:
            pending = self.memory.check_callbacks(chapter_num)
            for cb in pending:
                cb_id = cb.callback_data.get("_callback_id", "")
                if cb_id and cb_id not in callback_injected:
                    if agent.name in cb.callback_data.get("characters", [agent.name]):
                        retrieved.append(MemoryEntry(
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

        # B4: Activate Emotional Memory — retrieve memories by emotional tone
        emotional_memories = []
        for agent in agents:
            emotion = agent.emotional_state_str()
            if emotion not in ('neutral', None):
                emo_results = self.memory.retrieve_by_emotion(emotion, top_k=2)
                emotional_memories.extend(emo_results)

        # Deduplicate: add emotional memories not already in standard memories
        seen_texts = set(m.text for m in retrieved)
        for em in emotional_memories:
            if em.text not in seen_texts:
                retrieved.append(em)
                seen_texts.add(em.text)

        # ME6.1: Inject RAG entries as narrative transformations (not verbatim)
        for agent in agents:
            for mem in retrieved:
                if mem.source == "rag_corpus" and random.random() < 0.5:
                    if agent.name in mem.characters or not mem.characters:
                        emotion = mem.emotion_tags[0] if mem.emotion_tags else "distant"
                        trigger = mem.text[:30].strip()
                        agent.beliefs.discovered.append(
                            f"a {emotion} memory of {trigger} surfaced"
                        )

        # Query interpretations for each agent
        interpretations: list[InterpretationEntry] = []
        for agent in agents:
            interps = self.memory.query_interpretations(agent.name, top_k=2)
            for interp in interps:
                if interp.confidence > 0.5:
                    interpretations.append(interp)

        # 5. Build SceneBlueprint with ConflictResolver's scene type
        blueprint = SceneBlueprint(
            objective=objective,
            agent_states=agent_state_map,
            world=world,
            retrieved_memories=retrieved,
            interpretations=interpretations,
            scene_type=resolved_scene_type,
        )

        # 5b. NarrativeRetriever classifies memories into structured package
        if self.narrative_retriever is not None:
            blueprint.narrative_package = self.narrative_retriever.retrieve(
                objective, world, retrieved
            )

        # ---- HWSE: before_scene ----
        if self.enable_hwse and self._hwse is not None:
            scene_history = self._get_scene_history()
            blueprint = self._hwse.before_scene(
                agents=agents,
                world=world,
                memory=self.memory,
                scene_history=scene_history,
                scene_index=scene_index,
                total_scenes=total_scenes,
                base_blueprint=blueprint,
            )

        # 6. DramaticRealizer produces text
        scene = self.realizer.realize(blueprint)
        self.realizer.perceive_scene(scene)

        # ---- HWSE: after_scene (FULL mode only) ----
        if self.enable_hwse and self._hwse is not None and self._hwse_mode == HWSEMode.FULL:
            scene_history = self._get_scene_history()
            hwse_results = self._hwse.after_scene(
                scene=scene,
                agents=agents,
                world=world,
                memory=self.memory,
                scene_history=scene_history,
                chapter_num=chapter_num,
                scene_num=scene_index + 1,
            )
            # Apply revised scene if available
            if hwse_results.get("revised"):
                scene = hwse_results.get("revised_scene", scene)

        return scene

    def _get_scene_history(self) -> list[GeneratedScene]:
        """Get the current scene history from HWSE state if available."""
        if self._hwse is not None:
            return self._hwse.state.scene_history
        return []

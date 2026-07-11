from __future__ import annotations

import os
import time

from backend.v2.character_agent import CharacterAgent
from backend.v2.config import get_generation_backend, get_hwse_mode, is_hwse_enabled
from backend.v2.dramatic_realizer import DramaticRealizer
from backend.v2.generators.base import TextGenerator
from backend.v2.generators.hybrid_generator import HybridGenerator
from backend.v2.generators.voice_adapter import VoiceAdapter
from backend.v2.generators.ngram_generator import NGramGenerator
from backend.v2.conflict_resolver import ConflictResolver
from backend.v2.factories import build_character_agents
from backend.v2.hwse_pipeline import HWSEPipeline
from backend.v2.memory_system import MemorySystem
from backend.v2.narrative_retriever import NarrativeRetriever
from backend.v2.rag_bridge import RAGBridge
from backend.v2.pipeline import ScenePipeline
from backend.v2.state_update import StateUpdater
from backend.v2.story_planner import StoryPlanner
from backend.v2.types import (
    GeneratedChapter,
    GeneratedScene,
    GenerationRequest,
    GenerationResult,
    StoryMode,
    StoryPlan,
    WorldConstraints,
)
from backend.v2.world_engine.world_engine import WorldEngine
from backend.v2.world_state import WorldState
from backend.v2.arc_planner.arc_planner import ArcPlanner

_FRAGMENTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data_pipeline", "output", "character_memory_fragments.jsonl",
)
_BLUEPRINTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data_pipeline", "output", "scene_blueprints.jsonl",
)


class StoryEngineV2:
    """Orchestrator that runs the generation pipeline for all modes.

    SHORT, CHAPTER, and BOOK all pass through the same pipeline with
    parametric differences — no mode-specific code paths.

    When enable_hwse=True, the HWSE (Human-Synthetic Story Engine)
    passes run before and after each scene:
      - Emotional arcs are built and validated
      - Character listening tracks interpersonal dynamics
      - Interrogation checks consistency
      - Revision improves scene quality
      - Momentum extraction optimizes pacing
    """

    def __init__(
        self,
        world_state: WorldState | None = None,
        world_engine: WorldEngine | None = None,
        memory: MemorySystem | None = None,
        planner: StoryPlanner | None = None,
        arc_planner: "ArcPlanner | None" = None,
        conflict_resolver: ConflictResolver | None = None,
        realizer: DramaticRealizer | None = None,
        generator: TextGenerator | None = None,
        state_updater: StateUpdater | None = None,
        narrative_retriever: NarrativeRetriever | None = None,
        enable_hwse: bool | None = None,
        hwse_pipeline: HWSEPipeline | None = None,
    ) -> None:
        # If enable_hwse is not explicitly passed, fall back to env var
        if enable_hwse is None:
            enable_hwse = is_hwse_enabled()

        self.world_engine = world_engine or WorldEngine()
        self.world_state = world_state or self.world_engine
        self.rag_bridge = RAGBridge()
        self.memory = memory or MemorySystem()
        self.planner = planner or StoryPlanner(rag_bridge=self.rag_bridge)
        self.arc_planner = arc_planner or ArcPlanner(self.planner)
        self.conflict_resolver = conflict_resolver or ConflictResolver()
        self.realizer = realizer or DramaticRealizer()
        self.state_updater = state_updater or StateUpdater()
        self.narrative_retriever = narrative_retriever or NarrativeRetriever()
        self.enable_hwse = enable_hwse
        self._hwse = hwse_pipeline or (HWSEPipeline() if enable_hwse else None)
        self._hwse_mode = get_hwse_mode()

        # Build TextGenerator based on GENERATION_BACKEND
        backend = get_generation_backend()
        self.generator = generator
        if self.generator is None:
            _project = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            model_path = os.path.join(_project, "models", "mlx_transformer.pkl")
            if backend == "torch":
                try:
                    from backend.v2.generators.torch_model import TorchTransformerGenerator
                    if os.path.exists(model_path):
                        self.generator = TorchTransformerGenerator.load(model_path)
                    else:
                        print(f"Torch model not found at {model_path}")
                        self.generator = None
                except Exception as e:
                    print(f"Failed to load torch transformer: {e}")
                    self.generator = None
            elif backend == "mlx_transformer":
                try:
                    from backend.v2.generators.mlx_model import MLXTransformerGenerator
                    if os.path.exists(model_path):
                        self.generator = MLXTransformerGenerator.load(model_path)
                    else:
                        print(f"MLX model not found at {model_path}, falling back to hybrid")
                        self.generator = None
                except Exception as e:
                    print(f"Failed to load MLX transformer: {e}, falling back")
                    self.generator = None
            elif backend == "hybrid":
                try:
                    model_path = os.path.join(_project, "models", "ngram_5gram.pkl")
                    model_path_full = os.path.join(_project, "models", "ngram_5gram_full.pkl")
                    ngram = None
                    # Try each candidate; skip corrupt/truncated pickle files
                    for cand in (model_path, model_path_full):
                        if os.path.exists(cand):
                            try:
                                ngram = NGramGenerator.load(cand)
                                print(f"Loaded n-gram model from {cand}")
                                break
                            except Exception as load_err:
                                print(f"Skipping corrupt model {cand}: {load_err}")
                                ngram = None
                    if ngram is None:
                        # Train a small on-the-fly model if no valid model exists
                        ngram = NGramGenerator(order=5, temperature=0.85)
                        from backend.v2.generators.corpus_loader import CorpusLoader
                        loader = CorpusLoader(
                            os.path.join(_project, "data", "gutenberg")
                        )
                        sentences = loader.iter_sentences(max_files=10)
                        ngram.train(sentences)
                        # Persist so subsequent runs are fast
                        try:
                            ngram.save(model_path)
                            print(f"Saved on-the-fly model to {model_path}")
                        except Exception:
                            pass
                    self.generator = HybridGenerator(
                        ngram_generator=ngram,
                        voice_adapter=VoiceAdapter(),
                        mode="hybrid",
                        temperature=0.85,
                    )
                except Exception:
                    self.generator = None

        self.pipeline = ScenePipeline(
            conflict_resolver=self.conflict_resolver,
            realizer=self.realizer,
            generator=self.generator,
            memory=self.memory,
            narrative_retriever=self.narrative_retriever,
            enable_hwse=self.enable_hwse,
            hwse_pipeline=self._hwse,
            hwse_mode=self._hwse_mode,
        )

    async def generate(
        self, request: GenerationRequest
    ) -> GenerationResult:
        start = time.monotonic()

        # Propagate generation mode into MemorySystem so mode-aware lazy
        # subsystems initialize correctly:
        #   SHORT   -> episodic + semantic only
        #   CHAPTER -> + belief subsystem
        #   BOOK    -> full stack (all 5 lazy subsystems)
        self.memory.mode = request.story_mode.value.upper()

        world = await self.world_engine.build(request)

        agents = self._init_agents(request, world)

        # Register agents with pipeline for voice-aware dialogue
        self.pipeline.set_agents(agents)

        plan = self.arc_planner.plan(request, world)
        chapters: list[GeneratedChapter] = []

        for chapter_arc in plan.chapters:
            chapter = await self._generate_chapter(
                chapter_arc=chapter_arc,
                agents=agents,
                world=world,
                request=request,
            )
            chapters.append(chapter)

        elapsed = (time.monotonic() - start) * 1000

        if request.story_mode == StoryMode.SHORT and chapters:
            story_text = "\n".join(
                s.content for s in chapters[0].scenes
            )
        else:
            story_text = "\n\n".join(
                f"Chapter {ch.chapter_num}: {ch.title}\n" + "\n".join(
                    s.content for s in ch.scenes
                )
                for ch in chapters
            )

        total_words = sum(ch.word_count for ch in chapters)

        # Collect HWSE metrics if enabled
        hwse_metrics = self._collect_hwse_metrics()

        return GenerationResult(
            story_text=story_text,
            chapters=chapters,
            word_count=total_words,
            generation_time_ms=elapsed,
            hwse_metrics=hwse_metrics,
        )

    def _collect_hwse_metrics(self) -> dict:
        """Collect HWSE metrics for the current generation."""
        if self._hwse is None or not self.enable_hwse:
            return {}
        state = self._hwse.state
        return {
            "momentum_snapshots": len(state.momentum_history),
            "interrogation_passes": len(state.interrogation_results),
            "revision_plans": sum(len(p) for p in state.revision_plans),
            "listening_moments": len(
                getattr(getattr(self._hwse, 'listening_memory', None), '_moments', [])
            ),
            "emotional_arcs": len(state.emotional_arcs),
        }

    def generate_integration_report(self) -> dict:
        """Generate a runtime integration report of active subsystems."""
        report: dict = {
            "active_subsystems": [],
            "inactive_subsystems": [],
            "scene_modifications": 0,
            "memory_events": {},
            "planner_decisions": {},
            "conflict_adjustments": 0,
        }

        # Core subsystems
        if self.planner:
            report["active_subsystems"].append("StoryPlanner")
        if self.conflict_resolver:
            report["active_subsystems"].append("ConflictResolver")
        if self.realizer:
            report["active_subsystems"].append("DramaticRealizer")
        if self.memory:
            report["active_subsystems"].append("MemorySystem")
        if self.world_state:
            report["active_subsystems"].append("WorldState")
        if self.state_updater:
            report["active_subsystems"].append("StateUpdater")
        if self.enable_hwse and self._hwse:
            report["active_subsystems"].append("HWSEPipeline")

        # Memory snapshot
        if self.memory:
            snap = self.memory.snapshot()
            report["memory_events"] = {
                "episodic": snap.get("episodic_count", 0),
                "interpretation": snap.get("interpretation_count", 0),
                "consequence": snap.get("consequence_count", 0),
                "relationship_delta": snap.get("relationship_delta_count", 0),
                "semantic": snap.get("semantic_count", 0),
            }

        # HWSE status
        report["hwse_enabled"] = self.enable_hwse
        report["hwse_initialized"] = self._hwse is not None

        # Realizer repetition tracking report
        if self.realizer and hasattr(self.realizer, "report"):
            report["realizer"] = self.realizer.report()

        return report

    def generate_hwse_report(
        self,
    ) -> dict | None:
        """Generate the HWSE report if HWSE is enabled."""
        if self._hwse is not None:
            return self._hwse.generate_report(
                scene_history=self._hwse.state.scene_history,
                agents=self.pipeline._agents,
                memory=self.memory,
            )
        return None

    def _init_agents(
        self,
        request: GenerationRequest,
        world: WorldConstraints,
    ) -> list[CharacterAgent]:
        agents = build_character_agents(request.characters)

        if not agents:
            agents = build_character_agents([
                {
                    "name": "Arjun",
                    "role": "protagonist",
                    "traits": ["curious", "brave"],
                    "goals": ["uncover the truth"],
                },
                {
                    "name": "Maya",
                    "role": "antagonist",
                    "traits": ["deceptive", "ambitious"],
                    "goals": ["protect the secret"],
                },
            ])

        for agent in agents:
            self.memory.register_character(agent.name)
            agent.set_memory(self.memory)

        return agents

    def _resolve_chapter_count(self, request: GenerationRequest) -> int:
        if request.story_mode == StoryMode.SHORT:
            return 1
        if request.story_mode == StoryMode.CHAPTER:
            return 1
        return request.chapter_count

    async def _generate_chapter(
        self,
        chapter_arc: "ChapterArc",
        agents: list[CharacterAgent],
        world: WorldConstraints,
        request: GenerationRequest,
    ) -> GeneratedChapter:
        chapter_num = chapter_arc.chapter_num
        objectives = chapter_arc.objectives
        scene_count = len(objectives)
        scenes: list[GeneratedScene] = []

        for scene_index in range(scene_count):
            scene = self.pipeline.run(
                agents=agents,
                world=world,
                chapter_num=chapter_num,
                scene_index=scene_index,
                total_scenes=scene_count,
                objective=objectives[scene_index],
                story_mode=request.story_mode,
            )
            scenes.append(scene)

            self.state_updater.update_characters(
                agents, scene, world,
                memory=self.memory,
                chapter_num=chapter_num,
            )
            self.state_updater.record_scene_memory(
                self.memory, scene, chapter_num, scene_index + 1, agents
            )
            self.state_updater.update_perceptions(
                self.pipeline._agents, self.memory, scene,
                chapter_num, scene_index + 1,
            )

            # B1: Activate Interpretation Memory — each character interprets events
            self.state_updater.record_interpretations(
                self.memory, scene, agents, chapter_num, scene_index + 1,
            )

            # B2: Activate Consequence Tracking — record action outcomes
            self.state_updater.record_consequences(
                self.memory, scene, agents, chapter_num, scene_index + 1,
            )

            # B3: Activate Relationship Memory — detect relationship shifts
            self.state_updater.record_relationship_deltas(
                self.memory, scene, agents, chapter_num,
            )

            # Update HWSE scene history if enabled
            if self._hwse is not None:
                self._hwse.state.scene_history.append(scene)

        chapter_words = sum(s.word_count for s in scenes)

        return GeneratedChapter(
            chapter_num=chapter_num,
            title=self._chapter_title(chapter_num),
            scenes=scenes,
            summary=self._summarize(scenes, chapter_num),
            word_count=chapter_words,
        )

    def _chapter_title(self, chapter_num: int) -> str:
        titles = [
            "The Beginning",
            "Deepening Shadows",
            "Crossroads",
            "Revelations",
            "Turning Point",
            "Confrontation",
            "Aftermath",
            "New Alliances",
            "The Storm",
            "Resolution",
        ]
        if chapter_num <= len(titles):
            return titles[chapter_num - 1]
        return f"Chapter {chapter_num}"

    def _summarize(
        self, scenes: list[GeneratedScene], chapter_num: int
    ) -> str:
        purposes = [s.content[:80] for s in scenes[:3]]
        return f"Chapter {chapter_num}: " + " ".join(purposes)[:150]

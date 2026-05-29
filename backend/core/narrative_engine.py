from __future__ import annotations

import json
import logging
import random
import re
import traceback
import uuid
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from backend.core.chapter_generator import ChapterGenerator
from backend.core.data_models import Chapter
from backend.data.dataset_bridge import DatasetBridge
from backend.research.controllable_generator import ConditioningSpec, ControllableGenerator
from backend.research.emotional_arc_model import EmotionalArcModel
from backend.research.embedding_encoder import EmbeddingEncoder
from backend.research.embedding_memory import MemoryEntry
from backend.research.evaluation_pipeline import EvaluationPipeline
from backend.research.experiment_tracker import ExperimentTracker
from backend.research.memory_manager import EpisodicRecord, MemoryManager, SemanticFact
from backend.research.narrative_graph import NarrativeGraph, NarrativeNode
from backend.research.narrative_planner import NarrativePlanner
from backend.research.performance_profiler import PerformanceProfiler
from backend.research.rag_pipeline import RAGPipeline
from backend.research.research_config import ResearchEngineConfig
from backend.research.tension_source_model import TensionSourceModel
from backend.research.vector_store import SemanticMemoryRetriever, VectorStore

logger = logging.getLogger(__name__)


_DRIFT_IGNORE = {
    "A", "An", "And", "As", "At", "But", "By", "Every", "For", "From", "If",
    "In", "Into", "It", "No", "Not", "On", "Or", "So", "That", "The", "Then",
    "There", "This", "Through", "To", "When", "Where", "While", "With",
    "Chapter", "Grounding", "Historical Fiction",
}


class NarrativeEngine:
    def __init__(
        self,
        memory_manager: MemoryManager | None = None,
        planner: NarrativePlanner | None = None,
        rag_pipeline: RAGPipeline | None = None,
        evaluation_pipeline: EvaluationPipeline | None = None,
        controllable_generator: ControllableGenerator | None = None,
        experiment_tracker: ExperimentTracker | None = None,
        emotional_arc_model: EmotionalArcModel | None = None,
        research_config: ResearchEngineConfig | None = None,
        output_dir: str = "backend/research_output",
        dataset_bridge: DatasetBridge | None = None,
    ) -> None:
        self.research_config = research_config or ResearchEngineConfig.from_env()
        self.memory_manager = memory_manager or MemoryManager()
        self.planner = planner or NarrativePlanner()
        self.rag_pipeline = rag_pipeline or RAGPipeline()
        self.evaluation_pipeline = evaluation_pipeline or EvaluationPipeline()
        self.controllable_generator = controllable_generator or ControllableGenerator()
        self.experiment_tracker = experiment_tracker or ExperimentTracker(str(Path(output_dir) / "experiments.jsonl"))
        self.arc_model = emotional_arc_model or EmotionalArcModel()
        self.tension_model = TensionSourceModel()
        self.output_dir = output_dir
        self.dataset_bridge = dataset_bridge or DatasetBridge()
        self.graph = NarrativeGraph()
        self.profiler = PerformanceProfiler()
        self._provenance_log: list[dict[str, Any]] = []

    def generate_book(
        self,
        location: str = "Delhi",
        year: int = 1911,
        chapter_count: int = 10,
        genre: str | None = "Historical Fiction",
        theme: str | None = None,
        random_seed: int | None = None,
    ) -> dict[str, Any]:
        if random_seed is not None:
            random.seed(random_seed)
            try:
                import numpy as np  # type: ignore
                np.random.seed(random_seed)
            except Exception:  # noqa: BLE001
                pass

        session_id = str(uuid.uuid4())
        chapter_count = max(1, min(20, chapter_count))
        self._provenance_log = []
        self.arc_model = EmotionalArcModel()
        self.tension_model = TensionSourceModel()
        disabled_tiers = self.research_config.disabled_tiers() or self.memory_manager.disabled_tiers
        if not self.research_config.embedding_memory_enabled:
            disabled_tiers = set(disabled_tiers) | {"semantic"}
        self.memory_manager = MemoryManager(disabled_tiers=set(disabled_tiers))
        if self.research_config.embedding_memory_enabled:
            encoder = EmbeddingEncoder(model_name=self.research_config.embedding_model)
            self.memory_manager.semantic_retriever = SemanticMemoryRetriever(encoder, VectorStore())
        with self.profiler.measure("planning"):
            plan = self.planner.create_plan({
                "chapter_count": chapter_count,
                "genre": genre or "general",
                "setting": {"location": location, "year": year},
            })

        protagonist = self.dataset_bridge.safe_get_character()
        antagonist = self.dataset_bridge.safe_get_character()
        while antagonist == protagonist:
            antagonist = self.dataset_bridge.safe_get_character()
        role = self.dataset_bridge.get_role("modern")
        obj = self.dataset_bridge.get_narrative_object("Information")
        self.memory_manager.register_character(protagonist, role, ("curious", "persistent"))
        self.memory_manager.register_character(antagonist, "rival", ("secretive", "ambitious"))
        self.memory_manager.semantic.store(SemanticFact(location, "setting", f"{location} in {year}"))

        scene_builder = ChapterGenerator().scene_builder
        scene_builder.rag_pipeline = self.rag_pipeline
        scene_builder.reset_session()
        chapter_generator = ChapterGenerator(scene_builder=scene_builder, memory_manager=self.memory_manager)
        if not self.research_config.ml_scene_prediction_enabled:
            chapter_generator.hybrid_selector = None
            chapter_generator.scene_predictor = None
        chapters: list[Chapter] = []

        conditioning = ConditioningSpec(genre=genre, tone=theme, style_keywords=tuple(filter(None, (genre, theme))))
        base_context = {
            "location": location,
            "year": year,
            "genre": genre,
            "theme": theme,
            "protagonist": protagonist,
            "antagonist": antagonist,
            "role": role,
            "obj": obj,
            "total_chapters": chapter_count,
            "rag_pipeline": self.rag_pipeline,
            "conditioning": conditioning,
        }

        for chapter_num in range(1, chapter_count + 1):
            try:
                with self.profiler.measure("context_assembly"):
                    chapter_plan = plan.chapter_plans[chapter_num - 1]
                    context = base_context | self.memory_manager.assemble_chapter_context(chapter_num, [protagonist, antagonist])
                
                # Use dynamic tension from TensionSourceModel
                if "working_memory" in context:
                    context["working_memory"]["current_tension"] = self.tension_model.compute_current_tension()
                else:
                    context["working_memory"] = {"current_tension": self.tension_model.compute_current_tension()}
                    
                context["active_plot_threads"] = [
                    f"{location} {genre or 'story'} {beat.beat_type} {beat.required_scene_type} pressure"
                    for beat in chapter_plan.scene_beats
                ]
                context["chapter_plan"] = chapter_plan
                with self.profiler.measure("chapter_generation"):
                    chapter = chapter_generator.generate_chapter(chapter_num, context)
                chapters.append(chapter)
                drift_candidates: set[str] = set()
                for scene in chapter.scenes:
                    scene_names = set(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", scene.content))
                    known = set(self.memory_manager.characters)
                    for name in scene_names - known - {"Grounding", "Chapter"}:
                        first_word = name.split()[0]
                        if name in {location, genre, "The"} or first_word in _DRIFT_IGNORE:
                            continue
                        drift_candidates.add(name)
                if drift_candidates:
                    logger.debug(
                        "character_identity_drift_candidates",
                        extra={
                            "chapter_num": chapter_num,
                            "candidate_count": len(drift_candidates),
                            "sample": sorted(drift_candidates)[:10],
                        },
                    )
                for scene in chapter.scenes:
                    target = self.planner.get_target_tension(chapter_num)
                    if self.research_config.literary_intelligence_enabled:
                        self.arc_model.record(chapter_num, scene.scene_num, scene.tension_score, target)
                    self.memory_manager.episodic.append(EpisodicRecord(chapter_num, scene.scene_num, chapter.summary, [protagonist, antagonist], location))
                    self.memory_manager.working.append_summary(chapter.summary)
                    retriever = self.memory_manager.semantic_retriever
                    if self.research_config.embedding_memory_enabled and retriever is not None:
                        with self.profiler.measure("embedding_memory"):
                            memory_entry = MemoryEntry.from_scene(
                                scene,
                                {
                                    "chapter_num": chapter_num,
                                    "protagonist": protagonist,
                                    "antagonist": antagonist,
                                    "active_characters": [protagonist, antagonist],
                                },
                            )
                            retriever.add_memory(memory_entry)
                    node_id = f"c{chapter_num}s{scene.scene_num}"
                    self.graph.add_node(NarrativeNode(node_id, chapter_num, scene.scene_num, chapter.summary, [protagonist, antagonist], location))
                    for match in scene.content.split("[")[1:]:
                        if ":" in match and "]" in match:
                            source_id, rest = match.split(":", 1)
                            passage_id = rest.split("]", 1)[0]
                            self._provenance_log.append({"chapter_num": chapter_num, "scene_num": scene.scene_num, "source_id": source_id, "passage_id": passage_id})
                            
                    # Update dynamic tension source model based on scene content
                    self.tension_model.step_time()
                    if "conflict" in scene.content.lower() or "danger" in scene.content.lower():
                        self.tension_model.add_conflict("environmental", 0.3, "danger emerged")
                    if "argue" in scene.content.lower() or "disagree" in scene.content.lower():
                        self.tension_model.add_conflict("interpersonal", 0.4, "argument")
                        
            except Exception as exc:  # noqa: BLE001
                logger.error("chapter_generation_failed", extra={"chapter_num": chapter_num, "error": str(exc), "traceback": traceback.format_exc()})
                continue

        self.graph.infer_edges_from_timeline()
        if self.arc_model.is_collapsed():
            logger.warning("arc_collapse_warning", extra={"mad": self.arc_model.compute_mad()})
            
        references = []
        if self.rag_pipeline.is_available():
            for _, passage in self.rag_pipeline.index.documents:
                if passage.metadata.get("split") == "reference":
                    references.append(passage.text)
                    
        with self.profiler.measure("evaluation"):
            report = self.evaluation_pipeline.evaluate(
                chapters,
                self.memory_manager,
                plan,
                self.graph,
                references=references,
                genre=genre,
                conditioning=conditioning,
            )
        report.metrics.update(self.profiler.metrics())
        report.metrics.update({
            "phase_a_enabled": float(self.research_config.literary_intelligence_enabled),
            "phase_b_enabled": float(self.research_config.embedding_memory_enabled),
            "phase_c_enabled": float(self.research_config.ml_scene_prediction_enabled),
            "backward_compatibility_mode": float(self.research_config.backward_compatibility_mode),
        })
        session_dir = Path(self.output_dir) / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        self.memory_manager.serialize(self.output_dir, session_id)
        self.planner.serialize(session_id, self.output_dir)
        self.evaluation_pipeline.serialize_report(report, self.output_dir, session_id)
        if self.research_config.output_dashboard:
            self.evaluation_pipeline.serialize_dashboard([report], self.output_dir, session_id)
        self.graph.serialize(session_dir / "narrative_graph.json")
        (session_dir / "provenance.jsonl").write_text("\n".join(json.dumps(row, sort_keys=True) for row in self._provenance_log) + ("\n" if self._provenance_log else ""), encoding="utf-8")
        experiment = self.experiment_tracker.record(
            random_seed=random_seed,
            generation_parameters={"location": location, "year": year, "chapter_count": chapter_count, "genre": genre, "theme": theme},
            subsystem_config={
                "rag": self.rag_pipeline.is_available(),
                "memory_disabled": sorted(self.memory_manager.disabled_tiers),
                **self.research_config.to_dict(),
            },
            metrics=report.metrics,
        )
        return {
            "session_id": session_id,
            "chapters": chapters,
            "evaluation": asdict(report),
            "experiment": asdict(experiment),
            "provenance_count": len(self._provenance_log),
        }


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return value

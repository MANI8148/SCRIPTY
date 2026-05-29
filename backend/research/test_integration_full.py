from pathlib import Path

import pytest

from backend.core.data_models import Chapter, Scene, SceneType
from backend.core.narrative_engine import NarrativeEngine
from backend.research.embedding_encoder import EmbeddingEncoder
from backend.research.embedding_memory import MemoryEntry
from backend.research.performance_profiler import PerformanceProfiler
from backend.research.research_config import ResearchEngineConfig
from backend.research.scene_dataset_generator import SceneDatasetGenerator
from backend.research.vector_store import SemanticMemoryRetriever, VectorStore


def test_end_to_end_research_engine_all_phases_enabled(tmp_path):
    engine = NarrativeEngine(
        output_dir=str(tmp_path),
        research_config=ResearchEngineConfig(
            literary_intelligence_enabled=True,
            embedding_memory_enabled=True,
            ml_scene_prediction_enabled=True,
            output_dashboard=True,
        ),
    )

    result = engine.generate_book(location="Delhi", year=1911, chapter_count=1, random_seed=3)

    assert result["chapters"]
    metrics = result["evaluation"]["metrics"]
    assert metrics["phase_a_enabled"] == 1.0
    assert metrics["phase_b_enabled"] == 1.0
    assert metrics["phase_c_enabled"] == 1.0
    assert "performance_chapter_generation_seconds" in metrics
    assert Path(tmp_path, result["session_id"], "evaluation_dashboard.html").exists()


def test_backward_compatibility_mode_disables_research_heavy_phases(tmp_path):
    engine = NarrativeEngine(
        output_dir=str(tmp_path),
        research_config=ResearchEngineConfig(
            literary_intelligence_enabled=False,
            embedding_memory_enabled=False,
            ml_scene_prediction_enabled=False,
            backward_compatibility_mode=True,
            output_dashboard=False,
        ),
    )

    result = engine.generate_book(location="Mumbai", year=1950, chapter_count=1, random_seed=4)

    assert result["chapters"]
    metrics = result["evaluation"]["metrics"]
    assert metrics["backward_compatibility_mode"] == 1.0
    assert metrics["phase_b_enabled"] == 0.0


def test_embedding_batch_cache_and_vector_search_cache():
    encoder = EmbeddingEncoder()
    vectors = encoder.encode_batch(["archive clue", "archive clue", "rival threat"])
    assert len(vectors) == 3
    assert encoder.cache_info()["size"] == 2

    store = VectorStore()
    entry = MemoryEntry(
        text="Asha promised to protect the archive.",
        scene_id="c1s1",
        characters=["Asha"],
        importance=0.8,
        chapter_num=1,
        scene_num=1,
        memory_type="promise",
    )
    retriever = SemanticMemoryRetriever(encoder, store)
    retriever.add_memory(entry)
    first = retriever.retrieve("protect archive", top_k=1)
    second = retriever.retrieve("protect archive", top_k=1)
    assert first[0].scene_id == "c1s1"
    assert second[0].scene_id == "c1s1"


def test_full_subsystem_interaction_from_fixture(tmp_path):
    chapter = Chapter(
        chapter_num=1,
        title="Fixture",
        scenes=[
            Scene(1, SceneType.DESCRIPTION, "Asha entered the archive.", 4, 0.2),
            Scene(2, SceneType.DIALOGUE, "Asha revealed the map.", 5, 0.5),
        ],
        word_count=9,
        summary="Asha investigates.",
    )
    examples = SceneDatasetGenerator().examples_from_chapters([chapter], {"genre": "historical"})
    assert examples[0].target == "dialogue"

    profiler = PerformanceProfiler()
    with profiler.measure("fixture_generation"):
        assert examples
    assert profiler.metrics()["performance_fixture_generation_seconds"] >= 0.0


def test_fixtures_exist():
    fixture_dir = Path(__file__).parent / "fixtures"
    assert (fixture_dir / "scene_training_fixture.json").exists()
    assert (fixture_dir / "sample_book.json").exists()
    assert (fixture_dir / "memory_manifest.json").exists()

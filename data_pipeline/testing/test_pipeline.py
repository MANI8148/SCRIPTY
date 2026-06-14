import pytest
import tempfile
import os
import json
from pathlib import Path

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.schema.taxonomy import Category
from data_pipeline.storage.jsonl_store import JsonlStore
from data_pipeline.reporting.reporter import Reporter


class TestNarrativeFragment:
    def test_fragment_creation(self):
        frag = NarrativeFragment(
            text="Test narrative text.",
            source_book="Test Book",
            category="dialogue",
        )
        assert frag.id
        assert frag.source_book == "Test Book"
        assert frag.quality_score == 0.0

    def test_fragment_to_dict(self):
        frag = NarrativeFragment(text="Hello", category="emotions")
        d = frag.to_dict()
        assert d["text"] == "Hello"
        assert d["category"] == "emotions"

    def test_fragment_elite(self):
        frag = NarrativeFragment(text="Test", quality_score=0.9)
        assert frag.is_elite()

        frag2 = NarrativeFragment(text="Test", quality_score=0.6)
        assert not frag2.is_elite()

    def test_fragment_from_dict(self):
        data = {
            "text": "From dict",
            "source_book": "Book",
            "category": "actions",
        }
        frag = NarrativeFragment.from_dict(data)
        assert frag.text == "From dict"
        assert frag.category == "actions"


class TestJsonlStore:
    def test_append_and_count(self):
        store = JsonlStore[str]("/tmp/test_store.jsonl")
        store.clear()

        frag = NarrativeFragment(text="Test", source_book="Book")
        store.append(frag.to_dict())
        assert store.count() == 1

        store.clear()

    def test_append_batch(self):
        store = JsonlStore[str]("/tmp/test_batch.jsonl")
        store.clear()

        fragments = [NarrativeFragment(text=f"Test {i}") for i in range(5)]
        store.append_batch([f.to_dict() for f in fragments])
        assert store.count() == 5

        store.clear()


class TestReporter:
    def test_reporter_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = Reporter(tmpdir)
            assert reporter.output_dir.exists()

    def test_corpus_statistics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = Reporter(tmpdir)
            fragments = [
                NarrativeFragment(text="Frag 1", source_book="Book A", category="dialogue", quality_score=0.7),
                NarrativeFragment(text="Frag 2", source_book="Book A", category="emotions", emotion="joy", quality_score=0.8),
                NarrativeFragment(text="Frag 3", source_book="Book B", category="conflicts", conflict_type="internal", quality_score=0.9),
            ]
            stats = reporter._corpus_statistics(fragments)
            assert stats["total_fragments"] == 3
            assert stats["unique_books"] == 2
            assert stats["elite_fragments"] == 1


class TestPasses:
    def test_genre_pattern_pass(self):
        from data_pipeline.passes.pass10_genre_patterns import GenrePatternExtractionPass
        pass_instance = GenrePatternExtractionPass()
        frag = NarrativeFragment(text="The detective investigated the murder mystery.")
        results = pass_instance.execute([frag])
        assert results[0].genre_hint == "mystery"

    def test_conflict_pass(self):
        from data_pipeline.passes.pass6_conflicts import ConflictExtractionPass
        pass_instance = ConflictExtractionPass()
        frag = NarrativeFragment(text="She struggled with the moral dilemma of choosing right from wrong.")
        results = pass_instance.execute([frag])
        assert results[0].conflict_type == "moral"

    def test_worldbuilding_pass(self):
        from data_pipeline.passes.pass8_worldbuilding import WorldbuildingExtractionPass
        pass_instance = WorldbuildingExtractionPass()
        frag = NarrativeFragment(text="The ancient castle stood on a mountain overlooking the river valley.")
        results = pass_instance.execute([frag])
        assert results[0].location


class TestOrchestratorBasic:
    def test_orchestrator_creation(self):
        from data_pipeline.orchestrator import PipelineOrchestrator
        orch = PipelineOrchestrator({"output_dir": "/tmp/test_pipeline_output"})
        assert orch is not None
        assert hasattr(orch, 'parser')

    def test_sample_data_generation(self):
        from data_pipeline.orchestrator import PipelineOrchestrator
        orch = PipelineOrchestrator({"output_dir": "/tmp/test_sample_output"})
        path = orch._generate_sample_data()
        assert path is not None
        assert os.path.exists(path)


class TestTaxonomy:
    def test_category_values(self):
        assert Category.DIALOGUE.value == "dialogue"
        assert Category.ACTIONS.value == "actions"
        assert Category.EMOTIONS.value == "emotions"
        assert Category.CONFLICTS.value == "conflicts"

    def test_category_metadata(self):
        from data_pipeline.schema.taxonomy import get_category_metadata
        meta = get_category_metadata(Category.DIALOGUE)
        assert meta["group"] == "dialogue"
        assert meta["weight"] > 0

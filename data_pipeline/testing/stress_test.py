"""
Stress test for the Narrative Corpus Extraction Pipeline.

Tests the pipeline's ability to handle:
- 1000 books (simulated)
- 100,000+ fragments
- All extraction passes
- Memory and performance constraints
"""

import pytest
import time
import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.quality.quality_scorer import QualityScorer
from data_pipeline.quality.deduplicator import Deduplicator
from data_pipeline.passes.pass2_extraction import NarrativeFragmentExtractionPass
from data_pipeline.passes.pass5_emotions import EmotionExtractionPass
from data_pipeline.passes.pass6_conflicts import ConflictExtractionPass
from data_pipeline.passes.pass10_genre_patterns import GenrePatternExtractionPass


logger = logging.getLogger(__name__)


def generate_simulated_fragment(idx: int, book_id: int) -> NarrativeFragment:
    templates = [
        f'The {["dark","lone","ancient","mysterious","golden"][idx%5]} '
        f'{["warrior","city","forest","door","key","shadow","light","king"][idx%8]} '
        f'{["fell","rose","waited","burned","whispered","shattered"][idx%6]}. '
        f'{["He","She","They","It"][idx%4]} '
        f'{["knew","felt","saw","heard","remembered"][idx%5]} '
        f'{["everything","nothing","something","the truth","danger"][idx%5]}.',

        f'"I don\'t understand," {["he","she","they"][idx%3]} said, '
        f'{["frowning","smiling","whispering","shouting"][idx%4]}. '
        f'"It\'s {["too late","over","just beginning","dangerous"][idx%4]}."',

        f'The {["warm","cold","gentle","violent"][idx%4]} wind '
        f'{["carried","brought","whispered","swept"][idx%4]} '
        f'{["the scent","a sound","a memory","the truth"][idx%4]} '
        f'of {["forgotten times","distant lands","what was lost","the future"][idx%4]}.',
    ]

    template = templates[idx % len(templates)]
    return NarrativeFragment(
        text=template,
        source_book=f"Book_{book_id:04d}",
        author=f"Author_{book_id % 100:03d}",
        chapter=(idx % 20) + 1,
        scene=(idx % 5) + 1,
        paragraph=idx,
        category=["dialogue", "actions", "emotions", "conflicts", "worldbuilding"][idx % 5],
        emotion=["", "anger", "fear", "joy", "sadness", ""][idx % 6],
        emotion_intensity=0.3 + (idx % 7) * 0.1,
        tension=0.2 + (idx % 8) * 0.1,
        stakes=0.1 + (idx % 9) * 0.1,
        genre_hint=["mystery", "thriller", "romance", "fantasy", ""][idx % 5],
        participants=[f"Character_{chr(65 + (idx + i) % 26)}" for i in range(2)],
        quality_score=0.5 + (idx % 5) * 0.1,
    )


class TestStressTest:
    def test_bulk_fragment_creation(self):
        """Test creating 100,000 fragments"""
        count = 100000
        fragments = [generate_simulated_fragment(i, i // 100) for i in range(count)]
        assert len(fragments) == count
        assert len(set(f.source_book for f in fragments)) == count // 100

    def test_quality_scorer_throughput(self):
        """Test quality scoring throughput (10k fragments)"""
        fragments = [generate_simulated_fragment(i, 0) for i in range(10000)]
        scorer = QualityScorer()

        start = time.time()
        scored = scorer.score_fragments(fragments)
        elapsed = time.time() - start

        logger.info(f"Quality scored 10k fragments in {elapsed:.2f}s")
        assert len(scored) > 0
        assert elapsed < 30

    def test_deduplicator_fallback_throughput(self):
        """Test dedup fallback throughput"""
        fragments = [generate_simulated_fragment(i, i // 100) for i in range(10000)]
        dedup = Deduplicator()
        dedup._model = None

        start = time.time()
        result = dedup._fallback_dedup(fragments)
        elapsed = time.time() - start

        logger.info(f"Fallback dedup 10k fragments in {elapsed:.2f}s")
        assert len(result) > 0
        assert elapsed < 10

    def test_extraction_pass_throughput(self):
        """Test extraction pass on many fragments"""
        fragments = [generate_simulated_fragment(i, i // 100) for i in range(5000)]

        passes = [
            ("EmotionExtractionPass", EmotionExtractionPass()),
            ("ConflictExtractionPass", ConflictExtractionPass()),
            ("GenrePatternExtractionPass", GenrePatternExtractionPass()),
        ]

        for name, pass_instance in passes:
            start = time.time()
            result = pass_instance.execute(fragments)
            elapsed = time.time() - start
            logger.info(f"{name} processed 5k fragments in {elapsed:.2f}s")
            assert len(result) == len(fragments)
            assert elapsed < 30

    def test_memory_usage_light(self):
        """Verify memory is reasonable for 10k fragments"""
        import tracemalloc
        tracemalloc.start()

        fragments = [generate_simulated_fragment(i, i // 100) for i in range(10000)]
        current, peak = tracemalloc.get_traced_memory()

        mb_per_fragment = peak / len(fragments) / (1024 * 1024)
        logger.info(f"10k fragments memory: current={current/1024/1024:.1f}MB, "
                    f"peak={peak/1024/1024:.1f}MB, per_frag={mb_per_fragment:.4f}MB")

        tracemalloc.stop()
        assert mb_per_fragment < 0.1

    def test_jsonl_storage_throughput(self):
        """Test writing many fragments to JSONL"""
        import tempfile
        from data_pipeline.storage.jsonl_store import JsonlStore

        fragments = [generate_simulated_fragment(i, i // 100) for i in range(5000)]

        with tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False) as f:
            tmp_path = f.name

        try:
            store = JsonlStore.for_fragments(tmp_path)
            start = time.time()
            store.append_batch(fragments)
            elapsed = time.time() - start
            count = store.count()
            logger.info(f"Wrote {count} fragments in {elapsed:.2f}s")
            assert count == 5000
        finally:
            import os
            os.unlink(tmp_path)


class TestThousandBookSimulation:
    @pytest.mark.slow
    def test_simulate_100_books(self):
        """Simulate processing 100 books"""
        n_books = 100
        fragments_per_book = 1000
        total = n_books * fragments_per_book

        fragments = []
        start = time.time()

        for book_id in range(n_books):
            for frag_idx in range(fragments_per_book):
                idx = book_id * fragments_per_book + frag_idx
                frag = generate_simulated_fragment(idx, book_id)
                fragments.append(frag)

        creation_time = time.time() - start
        logger.info(f"Created {total} fragments from {n_books} books in {creation_time:.2f}s")

        scorer = QualityScorer()
        scored = scorer.score_fragments(fragments)
        logger.info(f"Quality scored: {len(scored)}/{total} passed")

        assert len(fragments) == total

    @pytest.mark.slow
    def test_end_to_end_small(self):
        """End-to-end pipeline test with 10 books"""
        from data_pipeline.orchestrator import PipelineOrchestrator

        orch = PipelineOrchestrator({
            "output_dir": "/tmp/stress_test_output",
        })

        sample_path = orch._generate_sample_data()
        results = orch.run(input_paths=[sample_path])

        assert results["status"] == "success"
        assert results["total_fragments"] > 0
        logger.info(f"Pipeline produced {results['total_fragments']} fragments "
                    f"({results['elite_fragments']} elite) in {results['elapsed_seconds']:.1f}s")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    pytest.main([__file__, '-v'])

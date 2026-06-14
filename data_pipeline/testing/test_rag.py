import pytest
import tempfile
import os
import json
from pathlib import Path
from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.rag.corpus_builder import CorpusBuilder


class TestCorpusBuilder:
    def test_build_entry(self):
        builder = CorpusBuilder()
        frag = NarrativeFragment(
            text="Test narrative text with interesting content.",
            source_book="Test Book",
            author="Test Author",
            chapter=1,
            scene=1,
            category="dialogue",
            subcategory="dialogue_argument",
            emotion="anger",
            genre_hint="thriller",
        )
        entry = builder._build_entry(frag)
        assert entry["source_book"] == "Test Book"
        assert entry["category"] == "dialogue"
        assert len(entry["retrieval_tags"]) > 0

    def test_corpus_output(self):
        builder = CorpusBuilder()
        fragments = [
            NarrativeFragment(text=f"Fragment {i} with some narrative content.") for i in range(5)
        ]
        for i, f in enumerate(fragments):
            f.embedding = [0.1] * 384
            f.quality_score = 0.7

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            tmp_path = f.name

        try:
            builder.build(fragments, tmp_path)
            with open(tmp_path) as f:
                lines = f.readlines()
            assert len(lines) == 5
            for line in lines:
                data = json.loads(line)
                assert "id" in data
                assert "text" in data
        finally:
            os.unlink(tmp_path)


class TestEmbeddingManager:
    def test_embedding_assignment(self):
        from data_pipeline.rag.embedding_builder import EmbeddingBuilder
        builder = EmbeddingBuilder()
        builder._model = None

        fragments = [NarrativeFragment(text=f"Test fragment {i}.") for i in range(3)]
        result = builder.embed_fragments(fragments)
        assert len(result) == 3
        for f in result:
            assert len(f.embedding) == 384

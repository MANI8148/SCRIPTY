from pathlib import Path

import pytest

from backend.research.memory_manager import (
    EpisodicRecord,
    MemoryManager,
    SemanticFact,
    SemanticMemory,
)


def test_character_record_is_immutable():
    manager = MemoryManager()
    record = manager.register_character("Asha", "archivist", ("careful",))
    with pytest.raises(Exception):
        record.name = "Other"  # type: ignore[misc]


def test_memory_context_and_serialization_round_trip(tmp_path: Path):
    manager = MemoryManager()
    manager.register_character("Asha", "archivist", ("careful",))
    manager.episodic.append(EpisodicRecord(1, 1, "Asha finds a clue", ["Asha"], "Delhi"))
    manager.semantic.store(SemanticFact("Delhi", "setting", "Imperial capital"))
    manager.working.append_summary("Asha finds a clue")
    context = manager.assemble_chapter_context(2, ["Asha"])
    assert context["characters"]["Asha"]["role"] == "archivist"
    assert context["episodic_records"]
    assert context["working_memory"]["recent_scene_summaries"] == ["Asha finds a clue"]
    path = manager.serialize(str(tmp_path), "session")
    restored = MemoryManager.deserialize(path)
    assert restored.get_character("Asha").traits == ("careful",)
    assert restored.episodic.get_recent(1)[0].event == "Asha finds a clue"


def test_memory_ablation_returns_empty_tiers():
    manager = MemoryManager(disabled_tiers={"episodic", "semantic", "working"})
    manager.register_character("Asha", "archivist")
    manager.episodic.append(EpisodicRecord(1, 1, "event"))
    context = manager.assemble_chapter_context(1, ["Asha"])
    assert context["episodic_records"] == []
    assert context["semantic_facts"] == []
    assert context["working_memory"] == {}


# ---------------------------------------------------------------------------
# SemanticMemory — task 8.2
# ---------------------------------------------------------------------------

class TestSemanticMemoryStore:
    """store() upserts by (entity_name, fact_type) key."""

    def test_store_and_retrieve_roundtrip(self):
        mem = SemanticMemory()
        fact = SemanticFact("Delhi", "setting", "Imperial capital", source_chapter=1)
        mem.store(fact)
        result = mem.retrieve("Delhi", "setting")
        assert result is fact

    def test_store_upserts_existing_key(self):
        mem = SemanticMemory()
        mem.store(SemanticFact("Asha", "trait", "cautious", source_chapter=1))
        updated = SemanticFact("Asha", "trait", "bold", source_chapter=3)
        mem.store(updated)
        assert mem.retrieve("Asha", "trait") is updated
        assert len(mem) == 1  # still one entry, not two

    def test_store_different_fact_types_same_entity(self):
        mem = SemanticMemory()
        mem.store(SemanticFact("Asha", "trait", "cautious"))
        mem.store(SemanticFact("Asha", "location", "Delhi"))
        assert len(mem) == 2
        assert mem.retrieve("Asha", "trait").value == "cautious"
        assert mem.retrieve("Asha", "location").value == "Delhi"


class TestSemanticMemoryRetrieve:
    """retrieve() does exact lookup; returns None for missing keys."""

    def test_retrieve_missing_returns_none(self):
        mem = SemanticMemory()
        assert mem.retrieve("Unknown", "trait") is None

    def test_retrieve_wrong_fact_type_returns_none(self):
        mem = SemanticMemory()
        mem.store(SemanticFact("Asha", "trait", "cautious"))
        assert mem.retrieve("Asha", "location") is None

    def test_retrieve_is_case_sensitive(self):
        mem = SemanticMemory()
        mem.store(SemanticFact("Asha", "trait", "cautious"))
        assert mem.retrieve("asha", "trait") is None


class TestSemanticMemoryRetrieveSimilarSubstring:
    """retrieve_similar() with vector_backend='none' uses substring matching."""

    def test_returns_empty_when_no_facts(self):
        mem = SemanticMemory(vector_backend="none")
        assert mem.retrieve_similar("capital") == []

    def test_substring_match_on_value(self):
        mem = SemanticMemory(vector_backend="none")
        mem.store(SemanticFact("Delhi", "setting", "Imperial capital of the Mughal empire"))
        results = mem.retrieve_similar("capital")
        assert len(results) == 1
        assert results[0].entity_name == "Delhi"

    def test_substring_match_on_entity_name(self):
        mem = SemanticMemory(vector_backend="none")
        mem.store(SemanticFact("Asha", "trait", "cautious"))
        results = mem.retrieve_similar("asha")
        assert len(results) == 1

    def test_top_k_limits_results(self):
        mem = SemanticMemory(vector_backend="none")
        for i in range(10):
            mem.store(SemanticFact(f"Entity{i}", "trait", "brave warrior"))
        results = mem.retrieve_similar("brave", top_k=3)
        assert len(results) <= 3

    def test_no_match_returns_empty(self):
        mem = SemanticMemory(vector_backend="none")
        mem.store(SemanticFact("Asha", "trait", "cautious"))
        assert mem.retrieve_similar("zzznomatch") == []


class TestSemanticMemoryRetrieveSimilarTfidf:
    """retrieve_similar() with vector_backend='tfidf' uses cosine similarity."""

    def test_tfidf_returns_relevant_fact(self):
        sklearn = pytest.importorskip("sklearn", reason="scikit-learn not installed")
        mem = SemanticMemory(vector_backend="tfidf")
        mem.store(SemanticFact("Delhi", "setting", "Imperial Mughal capital city"))
        mem.store(SemanticFact("Asha", "trait", "cautious and careful"))
        results = mem.retrieve_similar("Mughal empire capital", top_k=5)
        assert any(f.entity_name == "Delhi" for f in results)

    def test_tfidf_lazy_fit_on_first_query(self):
        pytest.importorskip("sklearn", reason="scikit-learn not installed")
        mem = SemanticMemory(vector_backend="tfidf")
        assert mem._tfidf_vectorizer is None
        mem.store(SemanticFact("Asha", "trait", "brave"))
        mem.retrieve_similar("brave")
        assert mem._tfidf_vectorizer is not None

    def test_tfidf_refits_after_store(self):
        pytest.importorskip("sklearn", reason="scikit-learn not installed")
        mem = SemanticMemory(vector_backend="tfidf")
        mem.store(SemanticFact("Asha", "trait", "brave"))
        mem.retrieve_similar("brave")  # fit once
        assert not mem._tfidf_dirty
        mem.store(SemanticFact("Ravi", "role", "merchant"))
        assert mem._tfidf_dirty  # dirty after new store
        mem.retrieve_similar("merchant")
        assert not mem._tfidf_dirty  # re-fit on next query

    def test_tfidf_top_k_respected(self):
        pytest.importorskip("sklearn", reason="scikit-learn not installed")
        mem = SemanticMemory(vector_backend="tfidf")
        for i in range(10):
            mem.store(SemanticFact(f"Entity{i}", "trait", f"warrior soldier fighter {i}"))
        results = mem.retrieve_similar("warrior soldier", top_k=3)
        assert len(results) <= 3

    def test_tfidf_empty_store_returns_empty(self):
        mem = SemanticMemory(vector_backend="tfidf")
        assert mem.retrieve_similar("anything") == []

    def test_tfidf_falls_back_to_substring_when_sklearn_missing(self, monkeypatch):
        """When sklearn is unavailable, tfidf backend falls back to substring matching."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name.startswith("sklearn"):
                raise ImportError(f"Mocked missing: {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        mem = SemanticMemory(vector_backend="tfidf")
        mem.store(SemanticFact("Asha", "trait", "cautious warrior"))
        # Should fall back to substring matching without raising
        results = mem.retrieve_similar("cautious")
        assert len(results) == 1
        assert results[0].entity_name == "Asha"


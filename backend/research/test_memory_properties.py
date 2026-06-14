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



# ---------------------------------------------------------------------------
# Task 3.1 — Context Assembly Enhancement tests
# ---------------------------------------------------------------------------

class TestAssembleChapterContextSubsystemFields:
    """
    Validates: Requirements 1.12, 2.12

    assemble_chapter_context() must populate chapter_plan, current_tension,
    ml_scene_predictions, and arc_stage in character_states when subsystems
    are provided.
    """

    # ------------------------------------------------------------------
    # chapter_plan field
    # ------------------------------------------------------------------

    def test_chapter_plan_populated_when_planner_provided(self):
        """chapter_plan is set from planner.get_chapter_plan() when planner given."""
        from backend.research.narrative_planner import NarrativePlanner

        manager = MemoryManager()
        manager.register_character("Asha", "archivist")

        planner = NarrativePlanner()
        planner.create_plan({"chapter_count": 5, "genre": "thriller"})

        context = manager.assemble_chapter_context(1, ["Asha"], planner=planner)

        assert context["chapter_plan"] is not None
        assert context["chapter_plan"].chapter_num == 1

    def test_chapter_plan_is_none_when_no_planner(self):
        """chapter_plan defaults to None when no planner is provided."""
        manager = MemoryManager()
        manager.register_character("Asha", "archivist")

        context = manager.assemble_chapter_context(1, ["Asha"])

        assert "chapter_plan" in context
        assert context["chapter_plan"] is None

    def test_chapter_plan_contains_scene_beats(self):
        """chapter_plan includes scene_beats with beat_type and target_tension."""
        from backend.research.narrative_planner import NarrativePlanner

        manager = MemoryManager()
        planner = NarrativePlanner()
        planner.create_plan({"chapter_count": 3})

        context = manager.assemble_chapter_context(2, planner=planner)

        plan = context["chapter_plan"]
        assert len(plan.scene_beats) > 0
        beat = plan.scene_beats[0]
        assert hasattr(beat, "beat_type")
        assert hasattr(beat, "target_tension")
        assert 0.0 <= beat.target_tension <= 1.0

    # ------------------------------------------------------------------
    # current_tension field
    # ------------------------------------------------------------------

    def test_current_tension_populated_when_tension_model_provided(self):
        """current_tension is set from tension_model.compute_current_tension()."""
        from backend.research.tension_source_model import TensionSourceModel

        manager = MemoryManager()
        tension_model = TensionSourceModel()
        tension_model.add_conflict("interpersonal", 0.7, "Rival threatens protagonist")

        context = manager.assemble_chapter_context(1, tension_model=tension_model)

        assert context["current_tension"] is not None
        assert isinstance(context["current_tension"], float)
        assert 0.0 <= context["current_tension"] <= 1.0

    def test_current_tension_is_none_when_no_tension_model(self):
        """current_tension defaults to None when no tension_model is provided."""
        manager = MemoryManager()
        context = manager.assemble_chapter_context(1)

        assert "current_tension" in context
        assert context["current_tension"] is None

    def test_current_tension_reflects_conflict_intensity(self):
        """current_tension value reflects the active conflict intensity."""
        from backend.research.tension_source_model import TensionSourceModel

        manager = MemoryManager()
        tension_model_low = TensionSourceModel()
        tension_model_high = TensionSourceModel()
        tension_model_high.add_conflict("interpersonal", 0.9, "High stakes conflict")

        ctx_low = manager.assemble_chapter_context(1, tension_model=tension_model_low)
        ctx_high = manager.assemble_chapter_context(1, tension_model=tension_model_high)

        # High conflict model should produce higher tension
        assert ctx_high["current_tension"] > ctx_low["current_tension"]

    # ------------------------------------------------------------------
    # ml_scene_predictions field
    # ------------------------------------------------------------------

    def test_ml_scene_predictions_populated_when_predictor_provided(self):
        """ml_scene_predictions is set from ml_predictors.rank_scene_candidates()."""
        from backend.research.scene_predictor import FrequencyScenePredictor

        manager = MemoryManager()
        predictor = FrequencyScenePredictor()

        context = manager.assemble_chapter_context(1, ml_predictors=predictor)

        assert context["ml_scene_predictions"] is not None
        assert isinstance(context["ml_scene_predictions"], dict)
        assert len(context["ml_scene_predictions"]) > 0

    def test_ml_scene_predictions_is_empty_dict_when_no_predictor(self):
        """ml_scene_predictions defaults to {} when no ml_predictors provided."""
        manager = MemoryManager()
        context = manager.assemble_chapter_context(1)

        assert "ml_scene_predictions" in context
        assert context["ml_scene_predictions"] == {}

    def test_ml_scene_predictions_are_normalized_probabilities(self):
        """ml_scene_predictions values sum to approximately 1.0."""
        from backend.research.scene_predictor import FrequencyScenePredictor

        manager = MemoryManager()
        predictor = FrequencyScenePredictor()

        context = manager.assemble_chapter_context(1, ml_predictors=predictor)

        total = sum(context["ml_scene_predictions"].values())
        assert abs(total - 1.0) < 1e-6

    # ------------------------------------------------------------------
    # arc_stage in character_states
    # ------------------------------------------------------------------

    def test_arc_stage_populated_when_arc_tracker_provided(self):
        """character_states[name]['arc_stage'] is set from arc_tracker.current_stage()."""
        from backend.research.character_arc_tracker import ArcStage, CharacterArcTracker

        manager = MemoryManager()
        manager.register_character("Asha", "archivist")

        tracker = CharacterArcTracker()
        tracker.track_progression("Asha", 1, ArcStage.discovering)

        context = manager.assemble_chapter_context(1, ["Asha"], arc_tracker=tracker)

        assert "arc_stage" in context["character_states"]["Asha"]
        # ArcStage.discovering.value == 1
        assert context["character_states"]["Asha"]["arc_stage"] == ArcStage.discovering.value

    def test_arc_stage_is_none_when_no_arc_tracker(self):
        """character_states[name]['arc_stage'] is None when no arc_tracker provided."""
        manager = MemoryManager()
        manager.register_character("Asha", "archivist")

        context = manager.assemble_chapter_context(1, ["Asha"])

        assert "arc_stage" in context["character_states"]["Asha"]
        assert context["character_states"]["Asha"]["arc_stage"] is None

    def test_arc_stage_is_none_for_untracked_character(self):
        """arc_stage is None for a character not tracked by the arc_tracker."""
        from backend.research.character_arc_tracker import CharacterArcTracker

        manager = MemoryManager()
        manager.register_character("Asha", "archivist")

        tracker = CharacterArcTracker()  # Asha not tracked

        context = manager.assemble_chapter_context(1, ["Asha"], arc_tracker=tracker)

        assert context["character_states"]["Asha"]["arc_stage"] is None

    # ------------------------------------------------------------------
    # character_states completeness
    # ------------------------------------------------------------------

    def test_character_states_include_all_required_fields(self):
        """character_states entries include arc_stage, active_goals, emotional_state,
        relationships, knowledge, and unresolved_conflicts."""
        manager = MemoryManager()
        manager.register_character("Asha", "archivist")
        mem = manager.get_character_memory("Asha")
        mem.track_goal("Find the manuscript", chapter_introduced=1, priority=0.8)
        mem.update_emotional_state(1, "fearful", intensity=0.7)
        mem.record_relationship("Ravi", "ally", strength=0.6)
        mem.add_knowledge("The vault is hidden", chapter_acquired=1)
        mem.add_conflict("Rival seeks same artifact", chapter_introduced=1)

        context = manager.assemble_chapter_context(1, ["Asha"])
        state = context["character_states"]["Asha"]

        assert "arc_stage" in state
        assert "active_goals" in state
        assert "emotional_state" in state
        assert "relationships" in state
        assert "knowledge" in state
        assert "unresolved_conflicts" in state

        assert len(state["active_goals"]) == 1
        assert state["emotional_state"]["primary_emotion"] == "fearful"
        assert len(state["relationships"]) == 1
        assert len(state["knowledge"]) == 1
        assert len(state["unresolved_conflicts"]) == 1

    # ------------------------------------------------------------------
    # Backward compatibility — all subsystems disabled
    # ------------------------------------------------------------------

    def test_backward_compat_no_subsystems_returns_valid_context(self):
        """Calling assemble_chapter_context() without any subsystem args still works."""
        manager = MemoryManager()
        manager.register_character("Asha", "archivist")
        manager.episodic.append(EpisodicRecord(1, 1, "Asha finds a clue", ["Asha"], "Delhi"))

        context = manager.assemble_chapter_context(1, ["Asha"])

        # Core fields still present
        assert "characters" in context
        assert "character_states" in context
        assert "episodic_records" in context
        assert "semantic_facts" in context
        assert "working_memory" in context
        assert "retrieved_memories" in context
        # New fields default gracefully
        assert context["chapter_plan"] is None
        assert context["current_tension"] is None
        assert context["ml_scene_predictions"] == {}

    def test_backward_compat_disabled_tiers_still_work(self):
        """Disabled tiers still produce empty results; new fields default to None/{}."""
        manager = MemoryManager(disabled_tiers={"episodic", "semantic", "working"})
        manager.register_character("Asha", "archivist")

        context = manager.assemble_chapter_context(1, ["Asha"])

        assert context["episodic_records"] == []
        assert context["semantic_facts"] == []
        assert context["working_memory"] == {}
        assert context["chapter_plan"] is None
        assert context["current_tension"] is None
        assert context["ml_scene_predictions"] == {}

    def test_all_subsystems_together(self):
        """All four subsystem params can be provided simultaneously."""
        from backend.research.character_arc_tracker import ArcStage, CharacterArcTracker
        from backend.research.narrative_planner import NarrativePlanner
        from backend.research.scene_predictor import FrequencyScenePredictor
        from backend.research.tension_source_model import TensionSourceModel

        manager = MemoryManager()
        manager.register_character("Asha", "archivist")

        planner = NarrativePlanner()
        planner.create_plan({"chapter_count": 5})

        tension_model = TensionSourceModel()
        tension_model.add_conflict("interpersonal", 0.6, "Conflict")

        predictor = FrequencyScenePredictor()

        tracker = CharacterArcTracker()
        tracker.track_progression("Asha", 1, ArcStage.confronting)

        context = manager.assemble_chapter_context(
            1,
            ["Asha"],
            planner=planner,
            tension_model=tension_model,
            ml_predictors=predictor,
            arc_tracker=tracker,
        )

        assert context["chapter_plan"] is not None
        assert context["current_tension"] is not None
        assert context["ml_scene_predictions"] != {}
        assert context["character_states"]["Asha"]["arc_stage"] == ArcStage.confronting.value

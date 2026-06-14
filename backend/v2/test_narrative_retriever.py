"""Tests for NarrativeRetriever — classification, dedup, package assembly."""

from backend.v2.narrative_retriever import NarrativeRetriever, _classify_memory
from backend.v2.types import (
    MemoryEntry,
    NarrativePackage,
    SceneBlueprint,
    SceneObjective,
    SceneType,
    WorldConstraints,
)


def _make_mem(text: str, **kwargs) -> MemoryEntry:
    return MemoryEntry(
        text=text,
        source=kwargs.pop("source", "test"),
        chapter_num=kwargs.pop("chapter_num", 1),
        scene_num=kwargs.pop("scene_num", 1),
        characters=kwargs.pop("characters", []),
        **kwargs,
    )


def _make_obj(scene_type: SceneType = SceneType.DIALOGUE) -> SceneObjective:
    return SceneObjective(
        purpose="test purpose",
        characters_involved=["A", "B"],
        location="test",
        conflict_type="test",
        required_tension=0.5,
        target_scene_type=scene_type,
        resolution_goal="test",
    )


def _make_world() -> WorldConstraints:
    return WorldConstraints(
        era="modern",
        tech_level="modern",
        tone="neutral",
        infrastructure=["roads"],
        transport=["cars"],
    )


# ---------------------------------------------------------------------------
# NarrativePackage
# ---------------------------------------------------------------------------


class TestNarrativePackage:
    def test_default_empty(self):
        pkg = NarrativePackage()
        assert pkg.populated_slots() == []
        assert pkg.total_entries() == 0

    def test_populated_slots(self):
        pkg = NarrativePackage(
            dialogue_examples=[_make_mem('"Hello."')],
            action_examples=[_make_mem("He ran.")],
        )
        assert set(pkg.populated_slots()) == {"dialogue_examples", "action_examples"}
        assert pkg.total_entries() == 2

    def test_multiple_entries_in_slot(self):
        pkg = NarrativePackage(
            sensory_examples=[
                _make_mem("The scent of rain."),
                _make_mem("Warm light filtered."),
                _make_mem("A cold breeze."),
            ],
        )
        assert pkg.populated_slots() == ["sensory_examples"]
        assert pkg.total_entries() == 3

    def test_all_slots_populated(self):
        names = [
            "dialogue_examples", "action_examples", "emotion_examples",
            "sensory_examples", "thought_examples", "body_language_examples",
            "reaction_examples", "relationship_examples",
        ]
        kw = {n: [_make_mem("x")] for n in names}
        pkg = NarrativePackage(**kw)
        assert len(pkg.populated_slots()) == 8
        assert pkg.total_entries() == 8


# ---------------------------------------------------------------------------
# _classify_memory
# ---------------------------------------------------------------------------


class TestClassifyMemory:
    def test_dialogue_via_quotes(self):
        mem = _make_mem('"I will not go," she said.')
        assert _classify_memory(mem) == "dialogue"

    def test_dialogue_via_verb(self):
        mem = _make_mem("He asked her where she had been. She replied calmly.")
        assert _classify_memory(mem) == "dialogue"

    def test_action(self):
        mem = _make_mem("He sprinted across the field and vaulted the fence.")
        assert _classify_memory(mem) == "action"

    def test_emotion(self):
        mem = _make_mem("Her hands trembled as tears streamed down her face.")
        assert _classify_memory(mem) == "emotion"

    def test_sensory(self):
        mem = _make_mem("The warm scent of jasmine filled the night air.")
        assert _classify_memory(mem) == "sensory"

    def test_thought(self):
        mem = _make_mem("He wondered if she had ever really loved him.")
        assert _classify_memory(mem) == "thought"

    def test_body_language(self):
        mem = _make_mem("She nodded slowly, avoiding his gaze.")
        assert _classify_memory(mem) == "body_language"

    def test_relationship(self):
        mem = _make_mem("His friend had become his bitterest enemy.")
        assert _classify_memory(mem) == "relationship"

    def test_reaction(self):
        mem = _make_mem("She recoiled as if struck.")
        assert _classify_memory(mem) == "reaction"

    def test_category_override(self):
        mem = _make_mem("Some text with no keywords.", category="action")
        assert _classify_memory(mem) == "action"

    def test_empty_text(self):
        mem = _make_mem("")
        assert _classify_memory(mem) == ""

    def test_emotion_tags_fallback(self):
        mem = _make_mem("Something happened that was meaningful.", emotion_tags=["fear"])
        assert _classify_memory(mem) == "emotion"

    def test_best_density_wins(self):
        mem = _make_mem(
            "She wondered, she pondered, she reflected deeply. "
            "The scent of roses filled the air."
        )
        assert _classify_memory(mem) == "thought"

    def test_no_match_returns_empty(self):
        mem = _make_mem("The table was made of wood. The chair was blue.")
        assert _classify_memory(mem) == ""


# ---------------------------------------------------------------------------
# NarrativeRetriever.retrieve
# ---------------------------------------------------------------------------


class TestNarrativeRetriever:
    def test_retrieve_empty_input(self):
        nr = NarrativeRetriever()
        obj = _make_obj()
        world = _make_world()
        pkg = nr.retrieve(obj, world, [])
        assert isinstance(pkg, NarrativePackage)
        assert pkg.total_entries() == 0

    def test_retrieve_classifies_correctly(self):
        nr = NarrativeRetriever()
        obj = _make_obj()
        world = _make_world()
        mems = [
            _make_mem('"Hello," she said.'),
            _make_mem("He sprinted across the field."),
            _make_mem("The scent of rain filled the air."),
        ]
        pkg = nr.retrieve(obj, world, mems)
        assert len(pkg.dialogue_examples) == 1
        assert len(pkg.action_examples) == 1
        assert len(pkg.sensory_examples) == 1
        assert pkg.total_entries() == 3

    def test_retrieve_dedup_by_text(self):
        nr = NarrativeRetriever()
        obj = _make_obj()
        world = _make_world()
        mems = [
            _make_mem('"Hello."', source="mem"),
            _make_mem('"Hello."', source="rag"),
        ]
        pkg = nr.retrieve(obj, world, mems)
        assert pkg.total_entries() == 1

    def test_retrieve_dialog_focus_for_dialogue_scene(self):
        nr = NarrativeRetriever()
        obj = _make_obj(SceneType.DIALOGUE)
        world = _make_world()
        mems = [
            _make_mem('"Hello," she said.'),
            _make_mem("He ran."),
        ]
        pkg = nr.retrieve(obj, world, mems)
        assert len(pkg.dialogue_examples) == 1

    def test_retrieve_action_focus_for_action_scene(self):
        nr = NarrativeRetriever()
        obj = _make_obj(SceneType.ACTION)
        world = _make_world()
        mems = [
            _make_mem("He sprinted and vaulted the fence."),
            _make_mem('"Hello," she said.'),
        ]
        pkg = nr.retrieve(obj, world, mems)
        assert len(pkg.action_examples) == 1

    def test_retrieve_unclassified_with_emotion_tags(self):
        nr = NarrativeRetriever()
        obj = _make_obj()
        world = _make_world()
        mems = [
            _make_mem("The table was made of wood.", emotion_tags=["sad"]),
        ]
        pkg = nr.retrieve(obj, world, mems)
        assert len(pkg.emotion_examples) == 1

    def test_retrieve_unclassified_high_relevance(self):
        nr = NarrativeRetriever()
        obj = _make_obj()
        world = _make_world()
        mems = [
            _make_mem("The table was made of wood.", relevance_score=0.5),
        ]
        pkg = nr.retrieve(obj, world, mems)
        assert len(pkg.emotion_examples) == 1

    def test_retrieve_mixed_types_deduped(self):
        nr = NarrativeRetriever()
        obj = _make_obj()
        world = _make_world()
        mems = [
            _make_mem('"Hello," she said.', characters=["A"]),
            _make_mem("He ran.", characters=["B"]),
            _make_mem("He ran.", characters=["C"]),
            _make_mem("The scent of rain.", characters=[]),
        ]
        pkg = nr.retrieve(obj, world, mems)
        assert pkg.total_entries() == 3

    def test_retrieve_source_diversity_prioritized(self):
        nr = NarrativeRetriever()
        obj = _make_obj()
        world = _make_world()
        callback_mem = _make_mem("A dark memory surfaced.", source="callback")
        rag_mem = _make_mem("A dark memory surfaced.", source="rag_corpus")
        mems = [callback_mem, rag_mem]
        pkg = nr.retrieve(obj, world, mems)
        assert pkg.total_entries() == 1


# ---------------------------------------------------------------------------
# DramaticRealizer integration tests
# ---------------------------------------------------------------------------


class TestDramaticRealizerBasic:
    def test_instantiation(self):
        from backend.v2.dramatic_realizer import DramaticRealizer
        dr = DramaticRealizer()
        assert dr is not None
        assert dr._generator is None

    def test_template_fallback(self):
        from backend.v2.dramatic_realizer import DramaticRealizer
        from backend.v2.types import SceneBlueprint, SceneType
        dr = DramaticRealizer()
        bp = SceneBlueprint(
            objective=_make_obj(),
            agent_states={},
            world=_make_world(),
            retrieved_memories=[],
        )
        result = dr.realize(bp)
        assert result.word_count > 0
        assert result.scene_type == SceneType.DIALOGUE

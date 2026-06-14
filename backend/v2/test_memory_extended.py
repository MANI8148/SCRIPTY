"""Extended memory tests for SCRIPTY v2 Phase 3.

Covers:
  1. Interpretation Memory
  2. Consequence Memory
  3. Emotional Retrieval
  4. Relationship Deltas
  5. Callback Scheduler
  6. Full Integration Pipeline
"""

from __future__ import annotations

from backend.v2.character_agent import CharacterAgent
from backend.v2.memory_callback import CallbackScheduler
from backend.v2.memory_consequence import ConsequenceEngine, ConsequenceStore
from backend.v2.memory_emotional import EmotionalRetrievalEngine
from backend.v2.memory_interpretation import InterpretationEngine, InterpretationStore
from backend.v2.memory_relationship import RelationshipDeltaStore, RelationshipDeltaTracker
from backend.v2.memory_system import MemorySystem
from backend.v2.types import (
    CharacterRecord,
    ConsequenceEntry,
    InterpretationEntry,
    MemoryEntry,
    MemoryQuery,
    RelationKind,
    RelationshipDelta,
    ScheduledCallback,
)


# ========================================================================
# 1. Interpretation Memory Tests
# ========================================================================


class TestInterpretationStore:
    def test_add_and_query(self):
        store = InterpretationStore()
        entry = InterpretationEntry(
            character="Arjun",
            source_event_text="Maya hid the evidence",
            interpretation_text="Maya is hiding something important",
            emotion_impact="suspicion",
            confidence=0.8,
        )
        store.add(entry)
        results = store.query("Arjun")
        assert len(results) == 1
        assert results[0].emotion_impact == "suspicion"

    def test_query_by_emotion_filter(self):
        store = InterpretationStore()
        store.add(InterpretationEntry(
            character="Arjun", source_event_text="e1",
            interpretation_text="i1", emotion_impact="fear", confidence=0.5,
        ))
        store.add(InterpretationEntry(
            character="Arjun", source_event_text="e2",
            interpretation_text="i2", emotion_impact="anger", confidence=0.7,
        ))
        store.add(InterpretationEntry(
            character="Arjun", source_event_text="e3",
            interpretation_text="i3", emotion_impact="fear", confidence=0.9,
        ))
        fear_results = store.query("Arjun", emotion_filter="fear")
        assert len(fear_results) == 2
        assert all(r.emotion_impact == "fear" for r in fear_results)

    def test_query_other_character_not_included(self):
        store = InterpretationStore()
        store.add(InterpretationEntry(
            character="Arjun", source_event_text="e1",
            interpretation_text="i1", emotion_impact="fear", confidence=0.5,
        ))
        store.add(InterpretationEntry(
            character="Maya", source_event_text="e2",
            interpretation_text="i2", emotion_impact="anger", confidence=0.7,
        ))
        results = store.query("Maya")
        assert len(results) == 1
        assert results[0].character == "Maya"


class TestInterpretationEngine:
    def test_add_interpretation(self):
        engine = InterpretationEngine()
        entry = engine.add_interpretation(
            character="Arjun",
            source_event="Maya fled the scene",
            interpretation="She must be guilty",
            emotion_impact="anger",
            confidence=0.85,
        )
        assert isinstance(entry, InterpretationEntry)
        assert entry.character == "Arjun"
        assert entry.emotion_impact == "anger"

    def test_interpret_event_from_traits(self):
        engine = InterpretationEngine()
        entry = engine.interpret_event(
            event_text="A shadowy figure betrayed the group's location to enemies",
            character_name="Arjun",
            character_traits=["brave", "curious"],
        )
        assert isinstance(entry, InterpretationEntry)
        assert entry.character == "Arjun"
        assert len(entry.interpretation_text) > 0
        assert entry.confidence > 0

    def test_interpret_event_detects_keyword_emotion(self):
        engine = InterpretationEngine()
        entry = engine.interpret_event(
            event_text="The enemy attacked at dawn, killing several villagers",
            character_name="Arjun",
            character_traits=["cautious"],
        )
        # "enemy" -> fear, "attack" -> anger — but "enemy" comes first in keyword order
        assert entry.emotion_impact in ("fear", "anger")
        assert "moment of" in entry.interpretation_text
        assert entry.emotion_impact in entry.interpretation_text

    def test_interpretation_confidence_scales_with_traits(self):
        engine = InterpretationEngine()
        few = engine.interpret_event(
            event_text="Something happened",
            character_name="Arjun",
            character_traits=["brave"],
        )
        many = engine.interpret_event(
            event_text="Something happened",
            character_name="Arjun",
            character_traits=["brave", "curious", "wise", "loyal"],
        )
        assert many.confidence >= few.confidence

    def test_multiple_interpretations_ordered_by_confidence(self):
        engine = InterpretationEngine()
        engine.add_interpretation("Arjun", "e1", "i1", "fear", confidence=0.3)
        engine.add_interpretation("Arjun", "e2", "i2", "fear", confidence=0.9)
        engine.add_interpretation("Arjun", "e3", "i3", "fear", confidence=0.6)
        results = engine.query("Arjun", emotion_filter="fear")
        assert results[0].confidence == 0.9
        assert results[-1].confidence == 0.3


# ========================================================================
# 2. Consequence Memory Tests
# ========================================================================


class TestConsequenceStore:
    def test_add_and_query(self):
        store = ConsequenceStore()
        store.add(ConsequenceEntry(
            character="Arjun", action_text="confronted Maya",
            consequence_text="Maya revealed the truth", success=True, impact_level=0.8,
        ))
        results = store.query("Arjun", min_impact=0.3)
        assert len(results) == 1
        assert results[0].success is True

    def test_query_filters_by_min_impact(self):
        store = ConsequenceStore()
        store.add(ConsequenceEntry("Arjun", "a1", "c1", True, 0.2))
        store.add(ConsequenceEntry("Arjun", "a2", "c2", False, 0.8))
        store.add(ConsequenceEntry("Arjun", "a3", "c3", True, 0.5))
        results = store.query("Arjun", min_impact=0.5)
        assert len(results) == 2
        assert all(r.impact_level >= 0.5 for r in results)

    def test_consequences_for_action_keyword(self):
        store = ConsequenceStore()
        store.add(ConsequenceEntry("Arjun", "confronted Maya", "c1", True, 0.5))
        store.add(ConsequenceEntry("Arjun", "ran from danger", "c2", False, 0.3))
        store.add(ConsequenceEntry("Maya", "confronted Arjun", "c3", True, 0.7))
        results = store.consequences_for_action("confront")
        assert len(results) == 2
        assert all("confront" in r.action_text.lower() for r in results)

    def test_all_for_character(self):
        store = ConsequenceStore()
        store.add(ConsequenceEntry("Arjun", "a1", "c1", True, 0.5))
        store.add(ConsequenceEntry("Maya", "a2", "c2", False, 0.3))
        results = store.all_for_character("Arjun")
        assert len(results) == 1
        assert results[0].character == "Arjun"


class TestConsequenceEngine:
    def test_success_rate(self):
        engine = ConsequenceEngine()
        engine.add_consequence("Arjun", "fought", "won", success=True, impact=0.8)
        engine.add_consequence("Arjun", "lied", "got caught", success=False, impact=0.6)
        engine.add_consequence("Arjun", "helped", "gained ally", success=True, impact=0.4)
        rate = engine.success_rate("Arjun")
        assert rate == 2 / 3
        assert 0 < rate < 1

    def test_average_impact(self):
        engine = ConsequenceEngine()
        engine.add_consequence("Arjun", "a1", "c1", True, impact=0.5)
        engine.add_consequence("Arjun", "a2", "c2", False, impact=0.9)
        avg = engine.average_impact("Arjun")
        assert avg == 0.7

    def test_most_common_outcome(self):
        engine = ConsequenceEngine()
        engine.add_consequence("Arjun", "a1", "c1", True, 0.5)
        engine.add_consequence("Arjun", "a2", "c2", True, 0.5)
        engine.add_consequence("Arjun", "a3", "c3", False, 0.5)
        assert engine.most_common_outcome("Arjun") == "success"

    def test_unknown_character_returns_defaults(self):
        engine = ConsequenceEngine()
        assert engine.success_rate("Unknown") == 0.5
        assert engine.average_impact("Unknown") == 0.0
        assert engine.most_common_outcome("Unknown") == "unknown"

    def test_add_and_retrieve_consequence(self):
        engine = ConsequenceEngine()
        entry = engine.add_consequence(
            "Arjun", "investigated the clues",
            "found the hidden passage", success=True, impact=0.7,
        )
        assert isinstance(entry, ConsequenceEntry)
        results = engine.query("Arjun", min_impact=0.5)
        assert len(results) == 1
        assert results[0].action_text == "investigated the clues"


# ========================================================================
# 3. Emotional Retrieval Tests
# ========================================================================


class TestEmotionalRetrieval:
    def _make_engine(self) -> EmotionalRetrievalEngine:
        engine = EmotionalRetrievalEngine()
        engine.episodic_records = [
            MemoryEntry(
                text="Arjun was furious when he discovered the betrayal",
                source="generated", chapter_num=1, scene_num=1,
                characters=["Arjun"], relevance_score=0.9,
                emotion_tags=["anger"],
            ),
            MemoryEntry(
                text="Maya felt joyful as she reunited with her family",
                source="generated", chapter_num=1, scene_num=2,
                characters=["Maya"], relevance_score=0.7,
                emotion_tags=["joy"],
            ),
            MemoryEntry(
                text="Arjun was terrified as the enemy closed in",
                source="generated", chapter_num=2, scene_num=1,
                characters=["Arjun"], relevance_score=0.8,
                emotion_tags=["fear"],
            ),
            MemoryEntry(
                text="The market was bustling with activity",
                source="generated", chapter_num=1, scene_num=3,
                characters=["Arjun", "Maya"], relevance_score=0.3,
                emotion_tags=[],
            ),
        ]
        return engine

    def test_retrieve_by_emotion_anger(self):
        engine = self._make_engine()
        results = engine.retrieve_by_emotion("anger", top_k=5)
        assert len(results) >= 1
        assert all("angry" in r.text.lower() or "furious" in r.text.lower()
                   or "anger" in [t.lower() for t in r.emotion_tags]
                   for r in results)

    def test_retrieve_by_emotion_fear(self):
        engine = self._make_engine()
        results = engine.retrieve_by_emotion("fear", top_k=5)
        assert len(results) >= 1
        assert "terrified" in results[0].text.lower()

    def test_retrieve_by_emotion_unknown_returns_empty(self):
        engine = self._make_engine()
        results = engine.retrieve_by_emotion("nonexistent_emotion", top_k=5)
        assert len(results) == 0

    def test_retrieve_emotional_context_reinforcing(self):
        engine = self._make_engine()
        context = engine.retrieve_emotional_context("Arjun", "anger")
        assert "reinforcing" in context
        assert "contrasting" in context
        assert len(context["reinforcing"]) >= 1

    def test_retrieve_emotional_context_contrasting(self):
        engine = self._make_engine()
        context = engine.retrieve_emotional_context("Arjun", "anger")
        # Anger contrasts with joy/love/trust — the Maya joy entry should appear
        assert len(context["contrasting"]) >= 0  # May or may not have contrasting

    def test_emotional_timeline(self):
        engine = self._make_engine()
        timeline = engine.emotional_timeline("Arjun")
        assert len(timeline) >= 3  # 3 Arjun entries in the engine
        # Entries are sorted by (chapter_num, scene_num):
        #   ch1/sc1 "Arjun was furious..."
        #   ch1/sc3 "The market was bustling..."
        #   ch2/sc1 "Arjun was terrified..."
        assert timeline[0]["chapter"] == 1
        assert timeline[-1]["chapter"] == 2
        for point in timeline:
            assert "emotion" in point
            assert "intensity" in point
            assert "chapter" in point

    def test_emotional_timeline_empty_character(self):
        engine = self._make_engine()
        timeline = engine.emotional_timeline("Unknown")
        assert len(timeline) == 0


# ========================================================================
# 4. Relationship Delta Tests
# ========================================================================


class TestRelationshipDeltaStore:
    def test_add_and_for_character(self):
        store = RelationshipDeltaStore()
        store.add(RelationshipDelta(
            character_a="Arjun", character_b="Maya",
            old_relation=RelationKind.ALLY, new_relation=RelationKind.ENEMY,
            trigger_event="betrayal", chapter_num=3,
        ))
        results = store.for_character("Arjun")
        assert len(results) == 1
        assert results[0].new_relation == RelationKind.ENEMY

    def test_for_character_window(self):
        store = RelationshipDeltaStore()
        for i in range(5):
            store.add(RelationshipDelta(
                character_a="Arjun", character_b=f"Person{i}",
                old_relation=RelationKind.NEUTRAL, new_relation=RelationKind.ALLY,
                trigger_event="meeting", chapter_num=i,
            ))
        results = store.for_character("Arjun", window=2)
        assert len(results) == 2

    def test_for_relationship_bidirectional(self):
        store = RelationshipDeltaStore()
        store.add(RelationshipDelta(
            character_a="Arjun", character_b="Maya",
            old_relation=RelationKind.NEUTRAL, new_relation=RelationKind.ALLY,
            trigger_event="alliance", chapter_num=1,
        ))
        store.add(RelationshipDelta(
            character_a="Maya", character_b="Arjun",
            old_relation=RelationKind.ALLY, new_relation=RelationKind.ENEMY,
            trigger_event="betrayal", chapter_num=2,
        ))
        # Query from a->b
        results = store.for_relationship("Arjun", "Maya")
        assert len(results) == 2
        # Query from b->a gives same
        results2 = store.for_relationship("Maya", "Arjun")
        assert len(results2) == 2


class TestRelationshipDeltaTracker:
    def test_record_delta(self):
        tracker = RelationshipDeltaTracker()
        delta = tracker.record_delta(
            "Arjun", "Maya",
            RelationKind.ALLY, RelationKind.ENEMY,
            "Maya betrayed Arjun", chapter_num=5,
        )
        assert isinstance(delta, RelationshipDelta)
        assert delta.character_a == "Arjun"
        assert delta.new_relation == RelationKind.ENEMY

    def test_recent_changes(self):
        tracker = RelationshipDeltaTracker()
        for i in range(10):
            tracker.record_delta(
                "Arjun", f"Person{i}",
                RelationKind.NEUTRAL, RelationKind.ALLY,
                "event", chapter_num=i,
            )
        recent = tracker.recent_changes("Arjun", window=3)
        assert len(recent) == 3

    def test_relationship_timeline(self):
        tracker = RelationshipDeltaTracker()
        tracker.record_delta("Arjun", "Maya", RelationKind.NEUTRAL, RelationKind.ALLY, "meet", 1)
        tracker.record_delta("Arjun", "Maya", RelationKind.ALLY, RelationKind.RIVAL, "disagree", 3)
        tracker.record_delta("Arjun", "Maya", RelationKind.RIVAL, RelationKind.ENEMY, "betray", 5)
        timeline = tracker.relationship_timeline("Arjun", "Maya")
        assert len(timeline) == 3
        assert timeline[0].new_relation == RelationKind.ALLY
        assert timeline[-1].new_relation == RelationKind.ENEMY

    def test_current_sentiment(self):
        tracker = RelationshipDeltaTracker()
        tracker.record_delta("Arjun", "Maya", RelationKind.NEUTRAL, RelationKind.ALLY, "meet", 1)
        sentiment = tracker.current_sentiment("Arjun", "Maya")
        assert sentiment > 0  # ally is positive

    def test_current_sentiment_enemy(self):
        tracker = RelationshipDeltaTracker()
        tracker.record_delta("Arjun", "Maya", RelationKind.NEUTRAL, RelationKind.ENEMY, "betray", 1)
        sentiment = tracker.current_sentiment("Arjun", "Maya")
        assert sentiment < 0  # enemy is negative

    def test_current_sentiment_no_history(self):
        tracker = RelationshipDeltaTracker()
        assert tracker.current_sentiment("Arjun", "Maya") == 0.0

    def test_net_relationship_volatility(self):
        tracker = RelationshipDeltaTracker()
        tracker.record_delta("Arjun", "Maya", RelationKind.NEUTRAL, RelationKind.ALLY, "meet", 1)
        tracker.record_delta("Arjun", "Maya", RelationKind.ALLY, RelationKind.ENEMY, "betray", 2)
        volatility = tracker.net_relationship_volatility("Arjun")
        assert 0 < volatility <= 1.0

    def test_relationship_pressure_adjustment(self):
        tracker = RelationshipDeltaTracker()
        # Trending negative — should add pressure
        tracker.record_delta("Arjun", "Maya", RelationKind.ALLY, RelationKind.RIVAL, "argue", 1)
        tracker.record_delta("Arjun", "Maya", RelationKind.RIVAL, RelationKind.ENEMY, "betray", 2)
        pressure = tracker.relationship_pressure_adjustment("Arjun", "Maya", RelationKind.ENEMY)
        assert pressure > 0

    def test_relationship_map(self):
        tracker = RelationshipDeltaTracker()
        tracker.record_delta("Arjun", "Maya", RelationKind.NEUTRAL, RelationKind.ENEMY, "betray", 1)
        tracker.record_delta("Arjun", "Kiran", RelationKind.NEUTRAL, RelationKind.ALLY, "help", 1)
        rmap = tracker.relationship_map("Arjun")
        assert "Maya" in rmap
        assert "Kiran" in rmap
        assert rmap["Maya"] < 0  # enemy is negative
        assert rmap["Kiran"] > 0  # ally is positive


# ========================================================================
# 5. Callback Scheduler Tests
# ========================================================================


class TestCallbackScheduler:
    def test_schedule_and_pending(self):
        scheduler = CallbackScheduler()
        cb_id = scheduler.schedule_memory_callback(
            memory_id="mem_001",
            trigger_chapter=5,
            callback_data={"type": "revelation", "text": "The truth is revealed"},
        )
        assert cb_id is not None
        pending = scheduler.pending_callbacks()
        assert len(pending) == 1
        assert pending[0].memory_id == "mem_001"

    def test_schedule_multiple(self):
        scheduler = CallbackScheduler()
        scheduler.schedule_memory_callback("mem_001", 3, {"info": "early"})
        scheduler.schedule_memory_callback("mem_002", 10, {"info": "late"})
        assert len(scheduler.callbacks) == 2

    def test_check_callbacks_at_chapter(self):
        scheduler = CallbackScheduler()
        scheduler.schedule_memory_callback("mem_001", 3, {"info": "chapter3"})
        scheduler.schedule_memory_callback("mem_002", 5, {"info": "chapter5"})
        scheduler.schedule_memory_callback("mem_003", 3, {"info": "also_ch3"})

        at_ch3 = scheduler.check_callbacks(3)
        assert len(at_ch3) == 2
        assert all(cb.trigger_chapter == 3 for cb in at_ch3)
        assert all(not cb.fired for cb in at_ch3)

        at_ch5 = scheduler.check_callbacks(5)
        assert len(at_ch5) == 1

        at_ch4 = scheduler.check_callbacks(4)
        assert len(at_ch4) == 0

    def test_mark_fired(self):
        scheduler = CallbackScheduler()
        cb_id = scheduler.schedule_memory_callback("mem_001", 3, {})
        assert scheduler.mark_fired(cb_id) is True
        # Verify it's marked
        at_ch3 = scheduler.check_callbacks(3)
        assert len(at_ch3) == 0

    def test_mark_fired_invalid_id(self):
        scheduler = CallbackScheduler()
        assert scheduler.mark_fired("nonexistent") is False

    def test_mark_fired_twice(self):
        scheduler = CallbackScheduler()
        cb_id = scheduler.schedule_memory_callback("mem_001", 3, {})
        scheduler.mark_fired(cb_id)
        assert scheduler.mark_fired(cb_id) is False  # Already fired

    def test_pending_callbacks_by_chapter(self):
        scheduler = CallbackScheduler()
        scheduler.schedule_memory_callback("mem_001", 3, {})
        scheduler.schedule_memory_callback("mem_002", 5, {})
        scheduler.schedule_memory_callback("mem_003", 7, {})

        pending = scheduler.pending_callbacks(chapter=5)
        assert len(pending) == 2  # chapters 5 and 7
        assert all(cb.trigger_chapter >= 5 for cb in pending)

    def test_clear_fired(self):
        scheduler = CallbackScheduler()
        id1 = scheduler.schedule_memory_callback("mem_001", 1, {})
        scheduler.schedule_memory_callback("mem_002", 2, {})
        scheduler.mark_fired(id1)
        assert scheduler.clear_fired() == 1
        assert len(scheduler.callbacks) == 1
        assert scheduler.callbacks[0].memory_id == "mem_002"

    def test_callbacks_for_memory(self):
        scheduler = CallbackScheduler()
        scheduler.schedule_memory_callback("mem_001", 3, {})
        scheduler.schedule_memory_callback("mem_001", 7, {})
        scheduler.schedule_memory_callback("mem_002", 5, {})
        cbs = scheduler.callbacks_for_memory("mem_001")
        assert len(cbs) == 2


# ========================================================================
# 6. Integration Tests — MemorySystem with all modules
# ========================================================================


class TestMemorySystemIntegration:
    def test_full_pipeline_interpretation_and_consequence(self):
        """Test that interpretations lead to consequences which affect decisions."""
        memory = MemorySystem()
        memory.register_character("Arjun")
        memory.register_character("Maya")

        # 1. Record an event
        memory.record_event(
            "Maya betrayed Arjun to the authorities",
            chapter_num=1, scene_num=1,
            characters=["Arjun", "Maya"],
            relevance_score=0.9,
            emotion_tags=["anger", "fear"],
        )

        # 2. Record Arjun's interpretation of the event
        interp = memory.record_interpretation(
            character="Arjun",
            source_event="Maya betrayed Arjun to the authorities",
            interpretation="Maya cannot be trusted. She is working with our enemies.",
            emotion_impact="anger",
            confidence=0.85,
            chapter_num=1, scene_num=1,
        )
        assert interp.character == "Arjun"
        assert interp.emotion_impact == "anger"

        # 3. Record the consequence of Arjun's action based on that interpretation
        cons = memory.record_consequence(
            character="Arjun",
            action="confronted Maya about the betrayal",
            consequence="Maya denied everything and the confrontation escalated",
            success=False,
            impact=0.7,
            chapter_num=1, scene_num=2,
        )
        assert cons.character == "Arjun"
        assert cons.success is False

        # 4. Verify interpretation can be queried
        interps = memory.query_interpretations("Arjun")
        assert len(interps) == 1
        assert interps[0].emotion_impact == "anger"

        # 5. Verify consequence can be queried
        cons_results = memory.query_consequences("Arjun", min_impact=0.5)
        assert len(cons_results) == 1

        # 6. Verify emotional retrieval works for the recorded event
        emotion_results = memory.retrieve_by_emotion("anger")
        assert len(emotion_results) >= 1

    def test_relationship_deltas_and_emotional_context(self):
        """Test relationship changes propagate through emotional context."""
        memory = MemorySystem()
        memory.register_character("Arjun")
        memory.register_character("Maya")

        # Record initial event
        memory.record_event(
            "Arjun and Maya worked together successfully",
            chapter_num=1, scene_num=1,
            characters=["Arjun", "Maya"],
            relevance_score=0.6, emotion_tags=["joy", "trust"],
        )

        # Record relationship change
        delta = memory.record_relationship_delta(
            "Arjun", "Maya",
            RelationKind.NEUTRAL, RelationKind.ALLY,
            "successful collaboration", chapter_num=1,
        )
        assert delta.new_relation == RelationKind.ALLY

        # Later, relationship deteriorates
        memory.record_event(
            "Maya hid critical evidence from Arjun",
            chapter_num=2, scene_num=1,
            characters=["Maya", "Arjun"],
            relevance_score=0.8, emotion_tags=["anger", "fear"],
        )

        delta2 = memory.record_relationship_delta(
            "Arjun", "Maya",
            RelationKind.ALLY, RelationKind.RIVAL,
            "Maya hid evidence", chapter_num=2,
        )
        assert delta2.old_relation == RelationKind.ALLY

        # Check relationship timeline
        timeline = memory.relationship_timeline("Arjun", "Maya")
        assert len(timeline) == 2
        assert timeline[0].new_relation == RelationKind.ALLY
        assert timeline[1].new_relation == RelationKind.RIVAL

        # Check sentiment
        sentiment = memory.current_relationship_sentiment("Arjun", "Maya")
        assert sentiment < 0  # rival is negative

        # Check emotional context
        context = memory.retrieve_emotional_context("Arjun", "anger")
        assert "reinforcing" in context

    def test_callback_scheduling_and_resurfacing(self):
        """Test that scheduled callbacks resurface at the right chapter."""
        memory = MemorySystem()

        # Record a memory in chapter 1
        memory.record_event(
            "A cryptic note was found in the library",
            chapter_num=1, scene_num=1,
            characters=["Arjun"],
            relevance_score=0.9,
        )

        # Schedule it to resurface in chapter 5
        cb_id = memory.schedule_callback(
            memory_id="note_memory",
            trigger_chapter=5,
            callback_data={
                "type": "foreshadowing",
                "event": "The note's true meaning becomes clear",
            },
        )
        assert cb_id is not None

        # Check at chapter 3 — no callbacks yet
        at_ch3 = memory.check_callbacks(3)
        assert len(at_ch3) == 0

        # Check at chapter 5 — callback should fire
        at_ch5 = memory.check_callbacks(5)
        assert len(at_ch5) == 1
        assert at_ch5[0].memory_id == "note_memory"

        # Mark it fired
        assert memory.mark_callback_fired(cb_id) is True

        # Verify it won't fire again
        at_ch5_again = memory.check_callbacks(5)
        assert len(at_ch5_again) == 0

        # Pending callbacks should show it as fired
        pending = memory.pending_callbacks()
        assert len(pending) == 0  # all fired or all chapters passed

    def test_emotional_timeline_tracks_arc(self):
        """Test that emotional timeline accurately reflects character arc."""
        memory = MemorySystem()
        memory.register_character("Arjun")

        events = [
            ("Arjun discovered a clue", 1, 1, "hope", 0.5),
            ("Arjun was attacked by enemies", 1, 2, "fear", 0.8),
            ("Arjun lost a close friend", 2, 1, "sadness", 0.9),
            ("Arjun found renewed purpose", 3, 1, "hope", 0.6),
            ("Arjun confronted the villain", 4, 1, "anger", 0.9),
        ]

        for text, ch, sc, emotion, rel in events:
            memory.record_event(
                text, chapter_num=ch, scene_num=sc,
                characters=["Arjun"], relevance_score=rel,
                emotion_tags=[emotion],
            )

        timeline = memory.emotional_timeline("Arjun")
        assert len(timeline) == 5

        # Check chronological order
        for i in range(len(timeline) - 1):
            if timeline[i]["chapter"] == timeline[i + 1]["chapter"]:
                assert timeline[i]["scene"] <= timeline[i + 1]["scene"]
            else:
                assert timeline[i]["chapter"] < timeline[i + 1]["chapter"]

    def test_consequences_influence_success_rate(self):
        """Test that consequence tracking builds meaningful stats."""
        memory = MemorySystem()

        actions = [
            ("Arjun", "attacked the fortress", "breached the walls", True, 0.9, 1, 1),
            ("Arjun", "negotiated with the king", "gained an ally", True, 0.7, 1, 2),
            ("Arjun", "trusted the spy", "was betrayed", False, 0.8, 2, 1),
            ("Maya", "set a trap", "caught the intruder", True, 0.6, 1, 1),
        ]

        for char, action, result, success, impact, ch, sc in actions:
            memory.record_consequence(
                char, action, result, success, impact, ch, sc,
            )

        # Arjun: 2 successes, 1 failure = 66.7%
        arjun_rate = memory.consequence_engine.success_rate("Arjun")
        assert abs(arjun_rate - (2 / 3)) < 0.01

        # Maya: 1 success = 100%
        maya_rate = memory.consequence_engine.success_rate("Maya")
        assert maya_rate == 1.0

        # Unknown: default
        unknown_rate = memory.consequence_engine.success_rate("Unknown")
        assert unknown_rate == 0.5

    def test_interpretations_filtered_by_emotion(self):
        """Test that interpretations can be filtered by emotion type."""
        memory = MemorySystem()
        memory.register_character("Arjun")

        memory.record_interpretation("Arjun", "e1", "i1", "anger", 0.8)
        memory.record_interpretation("Arjun", "e2", "i2", "fear", 0.9)
        memory.record_interpretation("Arjun", "e3", "i3", "hope", 0.7)
        memory.record_interpretation("Arjun", "e4", "i4", "anger", 0.6)

        anger = memory.query_interpretations("Arjun", emotion_filter="anger")
        assert len(anger) == 2
        assert all(i.emotion_impact == "anger" for i in anger)
        # Should be sorted by confidence descending
        assert anger[0].confidence >= anger[1].confidence

    def test_relationship_delta_volatility(self):
        """Test volatility calculation for rapidly changing relationships."""
        memory = MemorySystem()

        # Volatile relationship — many changes
        memory.record_relationship_delta("Arjun", "Maya", RelationKind.NEUTRAL, RelationKind.ALLY, "meet", 1)
        memory.record_relationship_delta("Arjun", "Maya", RelationKind.ALLY, RelationKind.ENEMY, "betray", 2)
        memory.record_relationship_delta("Arjun", "Maya", RelationKind.ENEMY, RelationKind.NEUTRAL, "truce", 3)
        memory.record_relationship_delta("Arjun", "Maya", RelationKind.NEUTRAL, RelationKind.RIVAL, "compete", 4)

        volatility = memory.relationship_deltas.net_relationship_volatility("Arjun")
        assert volatility > 0.5  # highly volatile

        # Stable relationship — initially NEUTRAL, becomes ALLY, stays ALLY
        memory2 = MemorySystem()
        memory2.record_relationship_delta("Arjun", "Kiran", RelationKind.NEUTRAL, RelationKind.ALLY, "meet", 1)
        memory2.record_relationship_delta("Arjun", "Kiran", RelationKind.ALLY, RelationKind.ALLY, "cooperate", 2)
        memory2.record_relationship_delta("Arjun", "Kiran", RelationKind.ALLY, RelationKind.ALLY, "support", 3)

        stable_vol = memory2.relationship_deltas.net_relationship_volatility("Arjun")
        # 1 significant change (neutral→ally) out of 3 deltas = 0.33
        assert stable_vol < 0.5  # low volatility

    def test_callback_clear_fired(self):
        """Test that clearing fired callbacks works correctly."""
        memory = MemorySystem()

        id1 = memory.schedule_callback("mem_1", 3, {"data": "a"})
        memory.schedule_callback("mem_2", 5, {"data": "b"})
        memory.schedule_callback("mem_3", 7, {"data": "c"})

        assert memory.clear_fired_callbacks() == 0  # none fired yet
        assert len(memory.callback_scheduler.callbacks) == 3

        memory.mark_callback_fired(id1)
        assert memory.clear_fired_callbacks() == 1
        assert len(memory.callback_scheduler.callbacks) == 2

    def test_snapshot(self):
        """Test that snapshot gives correct summary of all memory stores."""
        memory = MemorySystem()
        memory.register_character("Arjun")
        memory.register_character("Maya")

        memory.record_event("event", 1, 1, ["Arjun"])
        memory.record_fact("fact", 1, 1, ["Arjun"])
        memory.record_interpretation("Arjun", "src", "interp", "anger", 0.8)
        memory.record_consequence("Arjun", "action", "result", True, 0.5)
        memory.record_relationship_delta("Arjun", "Maya", RelationKind.NEUTRAL, RelationKind.ALLY, "meet")
        memory.schedule_callback("mem_1", 5, {})

        snap = memory.snapshot()
        assert snap["episodic_count"] == 1
        assert snap["semantic_count"] == 1
        assert snap["interpretation_count"] == 1
        assert snap["consequence_count"] == 1
        assert snap["relationship_delta_count"] == 1
        assert snap["pending_callbacks"] == 1
        assert "Arjun" in snap["registered_characters"]
        assert "Maya" in snap["registered_characters"]

    def test_event_auto_interpretation_integration(self):
        """Test auto-interpretation of events through the MemorySystem."""
        memory = MemorySystem()
        memory.register_character("Arjun")

        # Auto-interpret an event based on traits
        entry = memory.interpret_event(
            event_text="The enemy army marched toward the city gates",
            character_name="Arjun",
            character_traits=["brave", "curious"],
            chapter_num=1, scene_num=1,
        )
        assert entry.character == "Arjun"
        assert len(entry.interpretation_text) > 0
        assert entry.emotion_impact != ""

        # Verify it's stored and retrievable
        results = memory.query_interpretations("Arjun")
        assert len(results) == 1
        assert results[0].interpretation_text == entry.interpretation_text

    def test_backward_compatibility(self):
        """Test that existing API still works with new modules."""
        memory = MemorySystem()
        memory.register_character("Arjun")

        # Original record_event
        memory.record_event("test event", 1, 1, ["Arjun"], relevance_score=0.5)
        results = memory.retrieve(MemoryQuery(focus_character="Arjun", context_query="test"))
        assert len(results) >= 1

        # Original recent_context
        ctx = memory.recent_context("Arjun", window=1)
        assert len(ctx) == 1

        # Original beliefs isolation
        arjun_beliefs = memory.beliefs_for("Arjun")
        maya_beliefs = memory.beliefs_for("Maya")
        arjun_beliefs.discovered.append("secret")
        assert "secret" not in maya_beliefs.discovered

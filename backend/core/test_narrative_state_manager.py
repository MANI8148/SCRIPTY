"""
Unit tests for NarrativeStateManager (Task 11.7)

Tests cover:
- Character arc initialization (initialize_character_arcs)
- Plot thread creation (initialize_plot_threads)
- State transitions (advance_chapter, update_character_location, etc.)
- Continuity validation (check_continuity)
- Timeline consistency

Requirements: 8.7, 8.8, 8.9, 10.1-10.6, 11.1-11.6, 13.1-13.7
"""
import unittest

from backend.core.narrative_state_manager import (
    NarrativeStateManager,
    CharacterState,
    TimelineEvent,
    ObjectState,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

PROTAGONIST = "Alice"
ANTAGONIST = "Victor"
SETTING = {"location": "London", "year": 1920}
CHAPTER_COUNT = 10


def make_manager(chapter_count: int = CHAPTER_COUNT) -> NarrativeStateManager:
    """Return a freshly constructed NarrativeStateManager."""
    return NarrativeStateManager(
        protagonist=PROTAGONIST,
        antagonist=ANTAGONIST,
        setting=SETTING,
        chapter_count=chapter_count,
    )


# ---------------------------------------------------------------------------
# 1. Construction and basic initialisation
# ---------------------------------------------------------------------------

class TestConstruction(unittest.TestCase):
    """Verify that __init__ sets up state correctly."""

    def test_attributes_stored(self):
        mgr = make_manager()
        self.assertEqual(mgr.protagonist, PROTAGONIST)
        self.assertEqual(mgr.antagonist, ANTAGONIST)
        self.assertEqual(mgr.setting, SETTING)
        self.assertEqual(mgr.chapter_count, CHAPTER_COUNT)

    def test_both_characters_initialised(self):
        mgr = make_manager()
        self.assertIn(PROTAGONIST, mgr.character_states)
        self.assertIn(ANTAGONIST, mgr.character_states)

    def test_initial_location_from_setting(self):
        mgr = make_manager()
        self.assertEqual(mgr.character_states[PROTAGONIST].location, "London")
        self.assertEqual(mgr.character_states[ANTAGONIST].location, "London")

    def test_initial_adversary_relationship(self):
        mgr = make_manager()
        self.assertEqual(
            mgr.character_states[PROTAGONIST].relationships.get(ANTAGONIST),
            "adversary",
        )
        self.assertEqual(
            mgr.character_states[ANTAGONIST].relationships.get(PROTAGONIST),
            "adversary",
        )

    def test_arc_history_has_initial_snapshot(self):
        mgr = make_manager()
        self.assertEqual(len(mgr._character_arc_history[PROTAGONIST]), 1)
        self.assertEqual(len(mgr._character_arc_history[ANTAGONIST]), 1)

    def test_empty_plot_threads_on_init(self):
        mgr = make_manager()
        self.assertEqual(mgr.plot_threads, [])

    def test_empty_timeline_on_init(self):
        mgr = make_manager()
        self.assertEqual(mgr.timeline, [])

    def test_empty_object_states_on_init(self):
        mgr = make_manager()
        self.assertEqual(mgr.object_states, {})

    def test_invalid_chapter_count_raises(self):
        with self.assertRaises(ValueError):
            NarrativeStateManager(PROTAGONIST, ANTAGONIST, SETTING, chapter_count=0)

    def test_single_chapter_allowed(self):
        mgr = NarrativeStateManager(PROTAGONIST, ANTAGONIST, SETTING, chapter_count=1)
        self.assertEqual(mgr.chapter_count, 1)


# ---------------------------------------------------------------------------
# 2. Character arc initialisation
# ---------------------------------------------------------------------------

class TestCharacterArcInitialisation(unittest.TestCase):
    """Tests for initialize_character_arcs() — Requirements 10.2, 10.3, 10.4"""

    def setUp(self):
        self.mgr = make_manager()
        self.mgr.initialize_character_arcs()

    def test_arcs_created_for_both_characters(self):
        self.assertIn(PROTAGONIST, self.mgr._character_arcs)
        self.assertIn(ANTAGONIST, self.mgr._character_arcs)

    def test_protagonist_arc_has_four_stages(self):
        arc = self.mgr._character_arcs[PROTAGONIST]
        self.assertEqual(len(arc.arc_stages), 4)

    def test_antagonist_arc_has_four_stages(self):
        arc = self.mgr._character_arcs[ANTAGONIST]
        self.assertEqual(len(arc.arc_stages), 4)

    def test_arc_stage_names_are_correct(self):
        arc = self.mgr._character_arcs[PROTAGONIST]
        stage_names = [s["stage"] for s in arc.arc_stages]
        self.assertEqual(stage_names, ["unaware", "discovering", "confronting", "resolving"])

    def test_protagonist_initial_state_has_goals(self):
        arc = self.mgr._character_arcs[PROTAGONIST]
        self.assertIn("goals", arc.initial_state)
        self.assertIsInstance(arc.initial_state["goals"], list)
        self.assertGreater(len(arc.initial_state["goals"]), 0)

    def test_protagonist_initial_state_has_motivations(self):
        arc = self.mgr._character_arcs[PROTAGONIST]
        self.assertIn("motivations", arc.initial_state)

    def test_protagonist_initial_state_has_obstacles(self):
        arc = self.mgr._character_arcs[PROTAGONIST]
        self.assertIn("obstacles", arc.initial_state)

    def test_protagonist_initial_state_has_traits(self):
        arc = self.mgr._character_arcs[PROTAGONIST]
        self.assertIn("traits", arc.initial_state)

    def test_protagonist_final_state_has_goals(self):
        arc = self.mgr._character_arcs[PROTAGONIST]
        self.assertIn("goals", arc.final_state)

    def test_antagonist_initial_goals_include_power(self):
        arc = self.mgr._character_arcs[ANTAGONIST]
        goals_text = " ".join(arc.initial_state["goals"]).lower()
        self.assertIn("power", goals_text)

    def test_arc_character_name_matches(self):
        p_arc = self.mgr._character_arcs[PROTAGONIST]
        a_arc = self.mgr._character_arcs[ANTAGONIST]
        self.assertEqual(p_arc.character_name, PROTAGONIST)
        self.assertEqual(a_arc.character_name, ANTAGONIST)

    def test_arc_stage_chapter_ranges_are_valid(self):
        arc = self.mgr._character_arcs[PROTAGONIST]
        for stage in arc.arc_stages:
            start, end = stage["chapter_range"]
            self.assertGreaterEqual(start, 1)
            self.assertLessEqual(start, end)
            self.assertLessEqual(end, CHAPTER_COUNT)

    def test_arc_stages_cover_full_chapter_range(self):
        """The last stage's end should equal chapter_count."""
        arc = self.mgr._character_arcs[PROTAGONIST]
        last_end = arc.arc_stages[-1]["chapter_range"][1]
        self.assertEqual(last_end, CHAPTER_COUNT)

    def test_arc_initial_location_matches_setting(self):
        arc = self.mgr._character_arcs[PROTAGONIST]
        self.assertEqual(arc.initial_state.get("location"), "London")

    def test_idempotent_reinitialisation(self):
        """Calling initialize_character_arcs twice should not raise."""
        self.mgr.initialize_character_arcs()
        self.assertIn(PROTAGONIST, self.mgr._character_arcs)


# ---------------------------------------------------------------------------
# 3. Plot thread creation
# ---------------------------------------------------------------------------

class TestPlotThreadCreation(unittest.TestCase):
    """Tests for initialize_plot_threads() — Requirements 11.1-11.6"""

    def setUp(self):
        self.mgr = make_manager(chapter_count=10)
        self.mgr.initialize_plot_threads()

    def test_creates_at_least_three_threads(self):
        self.assertGreaterEqual(len(self.mgr.plot_threads), 3)

    def test_creates_at_most_five_threads(self):
        self.assertLessEqual(len(self.mgr.plot_threads), 5)

    def test_five_threads_for_ten_chapters(self):
        """Books with ≥10 chapters should get 5 threads."""
        self.assertEqual(len(self.mgr.plot_threads), 5)

    def test_four_threads_for_short_book(self):
        mgr = make_manager(chapter_count=5)
        mgr.initialize_plot_threads()
        self.assertEqual(len(mgr.plot_threads), 4)

    def test_thread_types_include_main_plot(self):
        types = [t.thread_type for t in self.mgr.plot_threads]
        self.assertIn("main_plot", types)

    def test_thread_types_include_subplot(self):
        types = [t.thread_type for t in self.mgr.plot_threads]
        self.assertIn("subplot", types)

    def test_thread_types_include_character_arc(self):
        types = [t.thread_type for t in self.mgr.plot_threads]
        self.assertIn("character_arc", types)

    def test_thread_types_include_mystery(self):
        types = [t.thread_type for t in self.mgr.plot_threads]
        self.assertIn("mystery", types)

    def test_all_threads_start_as_active(self):
        for thread in self.mgr.plot_threads:
            self.assertEqual(thread.status, "active")

    def test_all_threads_have_unique_ids(self):
        ids = [t.thread_id for t in self.mgr.plot_threads]
        self.assertEqual(len(ids), len(set(ids)))

    def test_main_plot_introduced_in_chapter_one(self):
        main = next(t for t in self.mgr.plot_threads if t.thread_type == "main_plot")
        self.assertEqual(main.introduced_chapter, 1)

    def test_main_plot_resolved_at_final_chapter(self):
        main = next(t for t in self.mgr.plot_threads if t.thread_type == "main_plot")
        self.assertEqual(main.resolved_chapter, CHAPTER_COUNT)

    def test_all_threads_have_foreshadowing(self):
        for thread in self.mgr.plot_threads:
            self.assertIsInstance(thread.foreshadowing_chapters, list)
            self.assertGreater(len(thread.foreshadowing_chapters), 0)

    def test_mystery_depends_on_main_plot(self):
        mystery = next(t for t in self.mgr.plot_threads if t.thread_type == "mystery")
        self.assertIn("main_plot_1", mystery.dependencies)

    def test_all_threads_have_descriptions(self):
        for thread in self.mgr.plot_threads:
            self.assertIsInstance(thread.description, str)
            self.assertGreater(len(thread.description), 0)

    def test_introduced_chapter_within_range(self):
        for thread in self.mgr.plot_threads:
            self.assertGreaterEqual(thread.introduced_chapter, 1)
            self.assertLessEqual(thread.introduced_chapter, CHAPTER_COUNT)

    def test_resolved_chapter_within_range(self):
        for thread in self.mgr.plot_threads:
            if thread.resolved_chapter is not None:
                self.assertGreaterEqual(thread.resolved_chapter, 1)
                self.assertLessEqual(thread.resolved_chapter, CHAPTER_COUNT)


# ---------------------------------------------------------------------------
# 4. State transitions — advance_chapter
# ---------------------------------------------------------------------------

class TestAdvanceChapter(unittest.TestCase):
    """Tests for advance_chapter() — Requirements 8.8, 10.5, 10.6, 13.2, 13.5, 13.6"""

    def setUp(self):
        self.mgr = make_manager()
        self.mgr.initialize_plot_threads()

    def test_advance_records_timeline_events(self):
        self.mgr.advance_chapter(1, ["The hero arrives in London."])
        self.assertEqual(len(self.mgr.timeline), 1)
        self.assertEqual(self.mgr.timeline[0].description, "The hero arrives in London.")

    def test_advance_records_correct_chapter_number(self):
        self.mgr.advance_chapter(1, ["Event A"])
        self.assertEqual(self.mgr.timeline[0].chapter_num, 1)

    def test_advance_records_multiple_events(self):
        self.mgr.advance_chapter(1, ["Event A", "Event B", "Event C"])
        self.assertEqual(len(self.mgr.timeline), 3)

    def test_advance_empty_events_list(self):
        self.mgr.advance_chapter(1, [])
        self.assertEqual(len(self.mgr.timeline), 0)

    def test_advance_creates_character_snapshot(self):
        self.mgr.advance_chapter(1, ["Event A"])
        # history[0] = initial, history[1] = after chapter 1
        self.assertEqual(len(self.mgr._character_arc_history[PROTAGONIST]), 2)

    def test_advance_snapshot_count_grows_per_chapter(self):
        for i in range(1, 4):
            self.mgr.advance_chapter(i, [f"Event {i}"])
        self.assertEqual(len(self.mgr._character_arc_history[PROTAGONIST]), 4)

    def test_advance_resolves_thread_at_resolution_chapter(self):
        """A thread with resolved_chapter=N should become 'resolved' after advance(N)."""
        # Find a thread and note its resolved_chapter
        thread = self.mgr.plot_threads[0]
        resolved_at = thread.resolved_chapter
        # Advance up to that chapter
        for i in range(1, resolved_at + 1):
            self.mgr.advance_chapter(i, [f"Event {i}"])
        self.assertEqual(thread.status, "resolved")

    def test_advance_does_not_resolve_thread_before_resolution_chapter(self):
        thread = self.mgr.plot_threads[0]
        resolved_at = thread.resolved_chapter
        if resolved_at and resolved_at > 1:
            self.mgr.advance_chapter(1, ["Early event"])
            self.assertEqual(thread.status, "active")

    def test_advance_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            self.mgr.advance_chapter(0, ["Bad chapter"])

    def test_advance_beyond_chapter_count_raises(self):
        with self.assertRaises(ValueError):
            self.mgr.advance_chapter(CHAPTER_COUNT + 1, ["Too far"])

    def test_advance_records_location_in_timeline_event(self):
        self.mgr.advance_chapter(1, ["Event A"])
        self.assertEqual(self.mgr.timeline[0].location, "London")

    def test_advance_records_characters_in_timeline_event(self):
        self.mgr.advance_chapter(1, ["Event A"])
        event = self.mgr.timeline[0]
        self.assertIn(PROTAGONIST, event.characters_involved)
        self.assertIn(ANTAGONIST, event.characters_involved)


# ---------------------------------------------------------------------------
# 5. Character state helpers
# ---------------------------------------------------------------------------

class TestCharacterStateHelpers(unittest.TestCase):
    """Tests for update_character_location, update_character_relationship,
    add_character_knowledge, and get_character_state."""

    def setUp(self):
        self.mgr = make_manager()

    # --- update_character_location ---

    def test_update_location_changes_current_state(self):
        self.mgr.update_character_location(PROTAGONIST, "Paris")
        self.assertEqual(self.mgr.character_states[PROTAGONIST].location, "Paris")

    def test_update_location_for_unknown_character_creates_state(self):
        self.mgr.update_character_location("NewChar", "Berlin")
        self.assertIn("NewChar", self.mgr.character_states)
        self.assertEqual(self.mgr.character_states["NewChar"].location, "Berlin")

    def test_location_persists_in_snapshot_after_advance(self):
        self.mgr.update_character_location(PROTAGONIST, "Paris")
        self.mgr.advance_chapter(1, ["Arrived in Paris"])
        snapshot = self.mgr._character_arc_history[PROTAGONIST][1]
        self.assertEqual(snapshot.location, "Paris")

    def test_location_unchanged_without_update(self):
        self.mgr.advance_chapter(1, ["Nothing changed"])
        snapshot = self.mgr._character_arc_history[PROTAGONIST][1]
        self.assertEqual(snapshot.location, "London")

    # --- update_character_relationship ---

    def test_update_relationship_changes_value(self):
        self.mgr.update_character_relationship(PROTAGONIST, ANTAGONIST, "ally")
        self.assertEqual(
            self.mgr.character_states[PROTAGONIST].relationships[ANTAGONIST], "ally"
        )

    def test_update_relationship_for_new_character(self):
        self.mgr.update_character_relationship(PROTAGONIST, "Sidekick", "friend")
        self.assertEqual(
            self.mgr.character_states[PROTAGONIST].relationships["Sidekick"], "friend"
        )

    def test_update_relationship_for_unknown_character_creates_state(self):
        self.mgr.update_character_relationship("Ghost", PROTAGONIST, "neutral")
        self.assertIn("Ghost", self.mgr.character_states)

    # --- add_character_knowledge ---

    def test_add_knowledge_stores_fact(self):
        self.mgr.add_character_knowledge(PROTAGONIST, "The artifact is in the vault.")
        self.assertIn(
            "The artifact is in the vault.",
            self.mgr.character_states[PROTAGONIST].knowledge,
        )

    def test_add_multiple_knowledge_facts(self):
        self.mgr.add_character_knowledge(PROTAGONIST, "Fact A")
        self.mgr.add_character_knowledge(PROTAGONIST, "Fact B")
        self.assertIn("Fact A", self.mgr.character_states[PROTAGONIST].knowledge)
        self.assertIn("Fact B", self.mgr.character_states[PROTAGONIST].knowledge)

    def test_add_knowledge_for_unknown_character_creates_state(self):
        self.mgr.add_character_knowledge("Stranger", "Secret")
        self.assertIn("Stranger", self.mgr.character_states)

    # --- get_character_state ---

    def test_get_character_state_chapter_zero_returns_initial(self):
        state = self.mgr.get_character_state(PROTAGONIST, 0)
        self.assertEqual(state["character_name"], PROTAGONIST)
        self.assertEqual(state["location"], "London")

    def test_get_character_state_after_advance(self):
        self.mgr.update_character_location(PROTAGONIST, "Paris")
        self.mgr.advance_chapter(1, ["Moved to Paris"])
        state = self.mgr.get_character_state(PROTAGONIST, 1)
        self.assertEqual(state["location"], "Paris")

    def test_get_character_state_unknown_character_returns_empty(self):
        state = self.mgr.get_character_state("Nobody", 0)
        self.assertEqual(state, {})

    def test_get_character_state_beyond_history_returns_latest(self):
        self.mgr.advance_chapter(1, ["Event"])
        # Request chapter 999 — should return the most recent snapshot
        state = self.mgr.get_character_state(PROTAGONIST, 999)
        self.assertIsNotNone(state)
        self.assertEqual(state["character_name"], PROTAGONIST)

    def test_get_character_state_returns_copy_of_relationships(self):
        state = self.mgr.get_character_state(PROTAGONIST, 0)
        state["relationships"]["tampered"] = "yes"
        # Original should be unaffected
        self.assertNotIn("tampered", self.mgr.character_states[PROTAGONIST].relationships)


# ---------------------------------------------------------------------------
# 6. Object tracking
# ---------------------------------------------------------------------------

class TestObjectTracking(unittest.TestCase):
    """Tests for register_object and update_object_state — Requirements 13.3"""

    def setUp(self):
        self.mgr = make_manager()

    def test_register_object_stores_state(self):
        self.mgr.register_object("Sword", location="Armory", owner=PROTAGONIST)
        self.assertIn("Sword", self.mgr.object_states)

    def test_register_object_location(self):
        self.mgr.register_object("Sword", location="Armory")
        self.assertEqual(self.mgr.object_states["Sword"].location, "Armory")

    def test_register_object_owner(self):
        self.mgr.register_object("Sword", owner=PROTAGONIST)
        self.assertEqual(self.mgr.object_states["Sword"].owner, PROTAGONIST)

    def test_register_object_defaults(self):
        self.mgr.register_object("Coin")
        obj = self.mgr.object_states["Coin"]
        self.assertEqual(obj.location, "unknown")
        self.assertIsNone(obj.owner)

    def test_update_object_location(self):
        self.mgr.register_object("Map", location="Library")
        self.mgr.update_object_state("Map", location="Vault")
        self.assertEqual(self.mgr.object_states["Map"].location, "Vault")

    def test_update_object_owner(self):
        self.mgr.register_object("Key", owner=PROTAGONIST)
        self.mgr.update_object_state("Key", owner=ANTAGONIST)
        self.assertEqual(self.mgr.object_states["Key"].owner, ANTAGONIST)

    def test_update_object_partial_update_preserves_other_fields(self):
        self.mgr.register_object("Ring", location="Tower", owner=PROTAGONIST)
        self.mgr.update_object_state("Ring", location="Dungeon")
        # Owner should remain unchanged
        self.assertEqual(self.mgr.object_states["Ring"].owner, PROTAGONIST)

    def test_update_unregistered_object_auto_registers(self):
        self.mgr.update_object_state("Ghost_Sword", location="Crypt")
        self.assertIn("Ghost_Sword", self.mgr.object_states)
        self.assertEqual(self.mgr.object_states["Ghost_Sword"].location, "Crypt")

    def test_object_persists_across_chapter_advance(self):
        self.mgr.register_object("Amulet", location="Temple", owner=PROTAGONIST)
        self.mgr.advance_chapter(1, ["Chapter event"])
        self.assertEqual(self.mgr.object_states["Amulet"].location, "Temple")


# ---------------------------------------------------------------------------
# 7. Continuity validation
# ---------------------------------------------------------------------------

class TestContinuityValidation(unittest.TestCase):
    """Tests for check_continuity() — Requirements 13.2, 13.6"""

    def setUp(self):
        self.mgr = make_manager()
        self.mgr.initialize_plot_threads()

    def test_no_issues_before_any_chapters(self):
        """Before advancing any chapters, unresolved threads are flagged."""
        issues = self.mgr.check_continuity()
        # All threads are unresolved — each should produce an issue
        unresolved_count = len([t for t in self.mgr.plot_threads if t.status != "resolved"])
        self.assertEqual(len(issues), unresolved_count)

    def test_no_temporal_issues_after_ordered_advances(self):
        for i in range(1, CHAPTER_COUNT + 1):
            self.mgr.advance_chapter(i, [f"Event {i}"])
        issues = self.mgr.check_continuity()
        temporal_issues = [iss for iss in issues if "Temporal inconsistency" in iss]
        self.assertEqual(temporal_issues, [])

    def test_all_threads_resolved_means_no_thread_issues(self):
        """After advancing all chapters, all threads should be resolved."""
        for i in range(1, CHAPTER_COUNT + 1):
            self.mgr.advance_chapter(i, [f"Event {i}"])
        issues = self.mgr.check_continuity()
        thread_issues = [iss for iss in issues if "Unresolved plot thread" in iss]
        self.assertEqual(thread_issues, [])

    def test_object_with_no_location_or_owner_flagged(self):
        self.mgr.register_object("Mystery_Box")
        # Default: location="unknown", owner=None — should be flagged
        issues = self.mgr.check_continuity()
        obj_issues = [iss for iss in issues if "Mystery_Box" in iss]
        self.assertGreater(len(obj_issues), 0)

    def test_object_with_known_location_not_flagged(self):
        self.mgr.register_object("Chest", location="Vault")
        issues = self.mgr.check_continuity()
        obj_issues = [iss for iss in issues if "Chest" in iss]
        self.assertEqual(obj_issues, [])

    def test_object_with_owner_not_flagged(self):
        self.mgr.register_object("Dagger", owner=PROTAGONIST)
        issues = self.mgr.check_continuity()
        obj_issues = [iss for iss in issues if "Dagger" in iss]
        self.assertEqual(obj_issues, [])

    def test_returns_list(self):
        issues = self.mgr.check_continuity()
        self.assertIsInstance(issues, list)

    def test_issues_are_strings(self):
        issues = self.mgr.check_continuity()
        for issue in issues:
            self.assertIsInstance(issue, str)

    def test_no_issues_when_all_resolved_and_no_bad_objects(self):
        for i in range(1, CHAPTER_COUNT + 1):
            self.mgr.advance_chapter(i, [f"Event {i}"])
        issues = self.mgr.check_continuity()
        self.assertEqual(issues, [])


# ---------------------------------------------------------------------------
# 8. Timeline consistency
# ---------------------------------------------------------------------------

class TestTimelineConsistency(unittest.TestCase):
    """Tests for timeline ordering and event recording — Requirements 13.1, 13.2"""

    def setUp(self):
        self.mgr = make_manager()

    def test_timeline_empty_initially(self):
        self.assertEqual(self.mgr.timeline, [])

    def test_timeline_grows_with_events(self):
        self.mgr.advance_chapter(1, ["A", "B"])
        self.assertEqual(len(self.mgr.timeline), 2)

    def test_timeline_events_have_correct_chapter_num(self):
        self.mgr.advance_chapter(1, ["Event 1"])
        self.mgr.advance_chapter(2, ["Event 2"])
        self.assertEqual(self.mgr.timeline[0].chapter_num, 1)
        self.assertEqual(self.mgr.timeline[1].chapter_num, 2)

    def test_timeline_events_are_in_order(self):
        for i in range(1, 6):
            self.mgr.advance_chapter(i, [f"Event {i}"])
        chapters = [e.chapter_num for e in self.mgr.timeline]
        self.assertEqual(chapters, sorted(chapters))

    def test_timeline_event_description_preserved(self):
        self.mgr.advance_chapter(1, ["The clock struck midnight."])
        self.assertEqual(self.mgr.timeline[0].description, "The clock struck midnight.")

    def test_timeline_event_location_matches_setting(self):
        self.mgr.advance_chapter(1, ["Something happened"])
        self.assertEqual(self.mgr.timeline[0].location, "London")

    def test_timeline_event_includes_both_characters(self):
        self.mgr.advance_chapter(1, ["Confrontation"])
        event = self.mgr.timeline[0]
        self.assertIn(PROTAGONIST, event.characters_involved)
        self.assertIn(ANTAGONIST, event.characters_involved)

    def test_multiple_events_same_chapter_all_recorded(self):
        events = ["First", "Second", "Third"]
        self.mgr.advance_chapter(1, events)
        recorded = [e.description for e in self.mgr.timeline]
        for ev in events:
            self.assertIn(ev, recorded)

    def test_timeline_accumulates_across_chapters(self):
        self.mgr.advance_chapter(1, ["Ch1 event"])
        self.mgr.advance_chapter(2, ["Ch2 event A", "Ch2 event B"])
        self.assertEqual(len(self.mgr.timeline), 3)

# ---------------------------------------------------------------------------
# 9. Active and unresolved plot thread queries
# ---------------------------------------------------------------------------

class TestPlotThreadQueries(unittest.TestCase):
    """Tests for get_active_plot_threads and get_unresolved_threads."""

    def setUp(self):
        self.mgr = make_manager()
        self.mgr.initialize_plot_threads()

    def test_get_active_threads_at_chapter_one(self):
        active = self.mgr.get_active_plot_threads(1)
        # All threads introduced at chapter 1 should be active
        introduced_at_1 = [t for t in self.mgr.plot_threads if t.introduced_chapter == 1]
        self.assertEqual(len(active), len(introduced_at_1))

    def test_get_active_threads_returns_list_of_dicts(self):
        active = self.mgr.get_active_plot_threads(1)
        self.assertIsInstance(active, list)
        for item in active:
            self.assertIsInstance(item, dict)

    def test_active_thread_dict_has_required_keys(self):
        active = self.mgr.get_active_plot_threads(1)
        required_keys = {
            "thread_id", "thread_type", "description",
            "introduced_chapter", "resolved_chapter",
            "foreshadowing_chapters", "dependencies", "status",
        }
        for item in active:
            self.assertTrue(required_keys.issubset(item.keys()))

    def test_resolved_thread_not_in_active_list(self):
        # Advance all chapters to resolve everything
        for i in range(1, CHAPTER_COUNT + 1):
            self.mgr.advance_chapter(i, [f"Event {i}"])
        active = self.mgr.get_active_plot_threads(CHAPTER_COUNT)
        self.assertEqual(active, [])

    def test_get_unresolved_threads_initially_all_threads(self):
        unresolved = self.mgr.get_unresolved_threads()
        self.assertEqual(len(unresolved), len(self.mgr.plot_threads))

    def test_get_unresolved_threads_returns_list_of_dicts(self):
        unresolved = self.mgr.get_unresolved_threads()
        self.assertIsInstance(unresolved, list)
        for item in unresolved:
            self.assertIsInstance(item, dict)

    def test_get_unresolved_threads_empty_after_all_resolved(self):
        for i in range(1, CHAPTER_COUNT + 1):
            self.mgr.advance_chapter(i, [f"Event {i}"])
        unresolved = self.mgr.get_unresolved_threads()
        self.assertEqual(unresolved, [])

    def test_thread_not_yet_introduced_not_in_active(self):
        """A thread introduced at chapter 3 should not appear at chapter 1."""
        late_threads = [
            t for t in self.mgr.plot_threads if t.introduced_chapter > 1
        ]
        if late_threads:
            active_at_1 = self.mgr.get_active_plot_threads(1)
            active_ids = {t["thread_id"] for t in active_at_1}
            for thread in late_threads:
                self.assertNotIn(thread.thread_id, active_ids)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()

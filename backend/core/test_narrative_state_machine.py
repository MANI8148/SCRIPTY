"""
Property-based test for narrative state machine validity (Task 11.6)

Tests cover:
- Property 5: Narrative state machine validity
  Validates: Requirements 13.7
  FOR ALL narrative elements, querying state at chapter N then at chapter N+1
  SHALL show only valid state transitions (state machine property).

  Specifically:
  - No teleportation: character locations only change when explicitly updated
    via update_character_location(); between advance_chapter() calls without
    explicit location updates the location must remain the same.
  - Temporal consistency: timeline events are recorded in non-decreasing
    chapter order; check_continuity() must report no temporal issues.
  - Object consistency: registered objects retain their last-set location/owner
    across chapter advances unless explicitly updated.
"""
import unittest

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.core.narrative_state_manager import NarrativeStateManager


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Valid character names: 3-20 chars, starts with uppercase letter
_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll")),
    min_size=3,
    max_size=20,
).filter(lambda n: n[0].isupper() and n.strip() == n)

# Valid location strings
_location_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll"),
        whitelist_characters=" ",
    ),
    min_size=3,
    max_size=50,
).filter(lambda x: x.strip() and not x.isspace())

# Setting dict
_setting_strategy = st.fixed_dictionaries({"location": _location_strategy})

# Chapter counts: 2-20 for BOOK mode
_chapter_count_strategy = st.integers(min_value=2, max_value=20)

# A list of event strings for a single chapter advance
_events_strategy = st.lists(
    st.text(min_size=5, max_size=80),
    min_size=0,
    max_size=5,
)

# Object names for tracking
_object_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll")),
    min_size=3,
    max_size=20,
).filter(lambda n: n[0].isupper() and n.strip() == n)


class TestNarrativeStateMachineValidity(unittest.TestCase):
    """
    Property 5: Narrative state machine validity

    **Validates: Requirements 13.7**

    FOR ALL narrative elements, querying state at chapter N then at chapter N+1
    SHALL show only valid state transitions (state machine property).
    """

    @given(
        protagonist=_name_strategy,
        antagonist=_name_strategy,
        setting=_setting_strategy,
        chapter_count=_chapter_count_strategy,
        events_per_chapter=st.lists(
            _events_strategy,
            min_size=2,
            max_size=20,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_no_teleportation_without_explicit_location_update(
        self,
        protagonist,
        antagonist,
        setting,
        chapter_count,
        events_per_chapter,
    ):
        """
        **Validates: Requirements 13.7**

        Property: When advance_chapter() is called WITHOUT any intervening
        update_character_location() call, the character's location in the
        snapshot recorded for chapter N+1 MUST equal the location recorded
        for chapter N.

        Characters cannot teleport between chapters without an explicit
        location update — this is the "no teleportation" rule.
        """
        if protagonist == antagonist:
            antagonist = antagonist + "X"

        chapters_to_advance = min(chapter_count, len(events_per_chapter))
        if chapters_to_advance < 2:
            return  # Need at least 2 chapters to compare consecutive snapshots

        manager = NarrativeStateManager(
            protagonist=protagonist,
            antagonist=antagonist,
            setting=setting,
            chapter_count=chapter_count,
        )

        # Advance through chapters WITHOUT any location updates
        for i, events in enumerate(events_per_chapter[:chapters_to_advance], start=1):
            manager.advance_chapter(chapter_num=i, events=events)

        # Verify: for each consecutive pair of snapshots, location must not change
        for char_name in (protagonist, antagonist):
            history = manager._character_arc_history[char_name]
            # history[0] = initial state, history[k] = state after chapter k
            for idx in range(len(history) - 1):
                loc_n = history[idx].location
                loc_n1 = history[idx + 1].location
                self.assertEqual(
                    loc_n,
                    loc_n1,
                    f"Character '{char_name}' teleported from '{loc_n}' to '{loc_n1}' "
                    f"between snapshot {idx} and {idx + 1} without an explicit "
                    f"location update (no-teleportation rule violated).",
                )

    @given(
        protagonist=_name_strategy,
        antagonist=_name_strategy,
        setting=_setting_strategy,
        chapter_count=_chapter_count_strategy,
        events_per_chapter=st.lists(
            _events_strategy,
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_temporal_consistency_of_timeline_events(
        self,
        protagonist,
        antagonist,
        setting,
        chapter_count,
        events_per_chapter,
    ):
        """
        **Validates: Requirements 13.7**

        Property: After advancing through any sequence of chapters in order,
        the timeline events recorded by the NarrativeStateManager MUST be in
        non-decreasing chapter order.  check_continuity() MUST NOT report any
        temporal inconsistency issues.

        This ensures temporal consistency: events happen in the order chapters
        are advanced, and no event can appear to precede an earlier chapter.
        """
        if protagonist == antagonist:
            antagonist = antagonist + "X"

        chapters_to_advance = min(chapter_count, len(events_per_chapter))
        if chapters_to_advance < 1:
            return

        manager = NarrativeStateManager(
            protagonist=protagonist,
            antagonist=antagonist,
            setting=setting,
            chapter_count=chapter_count,
        )

        # Advance chapters in strict ascending order (1, 2, 3, …)
        for i, events in enumerate(events_per_chapter[:chapters_to_advance], start=1):
            manager.advance_chapter(chapter_num=i, events=events)

        # Verify timeline events are in non-decreasing chapter order
        prev_chapter = 0
        for event in manager.timeline:
            self.assertGreaterEqual(
                event.chapter_num,
                prev_chapter,
                f"Temporal inconsistency: event '{event.description}' at chapter "
                f"{event.chapter_num} follows chapter {prev_chapter} — "
                f"timeline is not monotonically non-decreasing.",
            )
            prev_chapter = event.chapter_num

        # check_continuity() must not report temporal issues
        issues = manager.check_continuity()
        temporal_issues = [
            issue for issue in issues if "Temporal inconsistency" in issue
        ]
        self.assertEqual(
            temporal_issues,
            [],
            f"check_continuity() reported temporal issues after advancing chapters "
            f"in order: {temporal_issues}",
        )

    @given(
        protagonist=_name_strategy,
        antagonist=_name_strategy,
        setting=_setting_strategy,
        chapter_count=_chapter_count_strategy,
        object_name=_object_name_strategy,
        initial_location=_location_strategy,
        events_per_chapter=st.lists(
            _events_strategy,
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_object_consistency_across_chapter_advances(
        self,
        protagonist,
        antagonist,
        setting,
        chapter_count,
        object_name,
        initial_location,
        events_per_chapter,
    ):
        """
        **Validates: Requirements 13.7**

        Property: A registered object's location MUST remain unchanged across
        chapter advances unless update_object_state() is explicitly called.

        Objects cannot spontaneously change location between chapters — this
        enforces object consistency in the state machine.
        """
        if protagonist == antagonist:
            antagonist = antagonist + "X"

        chapters_to_advance = min(chapter_count, len(events_per_chapter))
        if chapters_to_advance < 1:
            return

        manager = NarrativeStateManager(
            protagonist=protagonist,
            antagonist=antagonist,
            setting=setting,
            chapter_count=chapter_count,
        )

        # Register an object at a known location
        manager.register_object(object_name, location=initial_location, owner=protagonist)

        # Advance through chapters WITHOUT updating the object
        for i, events in enumerate(events_per_chapter[:chapters_to_advance], start=1):
            manager.advance_chapter(chapter_num=i, events=events)

        # The object's location must still be the initial location
        obj_state = manager.object_states.get(object_name)
        self.assertIsNotNone(
            obj_state,
            f"Object '{object_name}' was registered but is missing from object_states.",
        )
        self.assertEqual(
            obj_state.location,
            initial_location,
            f"Object '{object_name}' location changed from '{initial_location}' to "
            f"'{obj_state.location}' without an explicit update_object_state() call "
            f"(object consistency rule violated).",
        )

    @given(
        protagonist=_name_strategy,
        antagonist=_name_strategy,
        setting=_setting_strategy,
        chapter_count=_chapter_count_strategy,
        new_location=_location_strategy,
        events_per_chapter=st.lists(
            _events_strategy,
            min_size=2,
            max_size=10,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_location_update_persists_in_subsequent_snapshots(
        self,
        protagonist,
        antagonist,
        setting,
        chapter_count,
        new_location,
        events_per_chapter,
    ):
        """
        **Validates: Requirements 13.7**

        Property: When update_character_location() is called before
        advance_chapter(N), the snapshot recorded for chapter N MUST reflect
        the new location, and all subsequent snapshots (N+1, N+2, …) MUST
        also reflect that location unless another update is made.

        This verifies that valid location transitions (with explicit updates)
        are correctly propagated through the state machine.
        """
        if protagonist == antagonist:
            antagonist = antagonist + "X"

        chapters_to_advance = min(chapter_count, len(events_per_chapter))
        if chapters_to_advance < 2:
            return

        manager = NarrativeStateManager(
            protagonist=protagonist,
            antagonist=antagonist,
            setting=setting,
            chapter_count=chapter_count,
        )

        # Advance chapter 1 without any location change
        manager.advance_chapter(chapter_num=1, events=events_per_chapter[0])

        # Update protagonist location before chapter 2
        manager.update_character_location(protagonist, new_location)

        # Advance remaining chapters without further location changes
        for i in range(2, chapters_to_advance + 1):
            manager.advance_chapter(
                chapter_num=i,
                events=events_per_chapter[i - 1],
            )

        # All snapshots from index 2 onward (after chapter 2 advance) must
        # reflect new_location for the protagonist
        history = manager._character_arc_history[protagonist]
        # history[0] = initial, history[1] = after ch1, history[2] = after ch2, …
        for idx in range(2, len(history)):
            self.assertEqual(
                history[idx].location,
                new_location,
                f"Protagonist location at snapshot {idx} should be '{new_location}' "
                f"(set before chapter 2 advance) but got '{history[idx].location}'.",
            )

    @given(
        protagonist=_name_strategy,
        antagonist=_name_strategy,
        setting=_setting_strategy,
        chapter_count=_chapter_count_strategy,
        events_per_chapter=st.lists(
            _events_strategy,
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_state_snapshot_count_matches_chapters_advanced(
        self,
        protagonist,
        antagonist,
        setting,
        chapter_count,
        events_per_chapter,
    ):
        """
        **Validates: Requirements 13.7**

        Property: After advancing K chapters, the character arc history for
        each character MUST contain exactly K+1 snapshots (1 initial + K
        chapter snapshots).

        This verifies the state machine records exactly one transition per
        chapter — no skipped or duplicated states.
        """
        if protagonist == antagonist:
            antagonist = antagonist + "X"

        chapters_to_advance = min(chapter_count, len(events_per_chapter))
        if chapters_to_advance < 1:
            return

        manager = NarrativeStateManager(
            protagonist=protagonist,
            antagonist=antagonist,
            setting=setting,
            chapter_count=chapter_count,
        )

        for i, events in enumerate(events_per_chapter[:chapters_to_advance], start=1):
            manager.advance_chapter(chapter_num=i, events=events)

        expected_snapshots = chapters_to_advance + 1  # initial + one per chapter

        for char_name in (protagonist, antagonist):
            history = manager._character_arc_history[char_name]
            self.assertEqual(
                len(history),
                expected_snapshots,
                f"Character '{char_name}' should have {expected_snapshots} snapshots "
                f"(1 initial + {chapters_to_advance} chapter advances) but has "
                f"{len(history)}.",
            )


if __name__ == "__main__":
    unittest.main()

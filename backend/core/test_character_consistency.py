"""
Property-based test for character consistency across chapters (Task 11.5)

Tests cover:
- Property 4: Character consistency across chapters
  Validates: Requirements 8.9
  For any multi-chapter book, character names and traits stored in the
  NarrativeStateManager SHALL remain identical across all chapter state
  snapshots (character names never change). The initial adversary relationship
  is also preserved unless explicitly changed.
"""
import unittest

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.core.narrative_state_manager import NarrativeStateManager


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Generate valid character names: 3-20 chars, starts with uppercase letter
_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll")),
    min_size=3,
    max_size=20,
).filter(lambda n: n[0].isupper() and n.strip() == n)

# Generate a setting dict with a location string
_setting_strategy = st.fixed_dictionaries(
    {
        "location": st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"),
                whitelist_characters=" ",
            ),
            min_size=3,
            max_size=50,
        ).filter(lambda x: x.strip() and not x.isspace())
    }
)

# Chapter counts for BOOK mode: 2-20 chapters
_chapter_count_strategy = st.integers(min_value=2, max_value=20)

# A list of event strings for a single chapter advance
_events_strategy = st.lists(
    st.text(min_size=5, max_size=80),
    min_size=0,
    max_size=5,
)


class TestCharacterConsistency(unittest.TestCase):
    """
    Property 4: Character consistency across chapters

    **Validates: Requirements 8.9**

    FOR ALL multi-chapter books, the protagonist and antagonist names stored
    in the NarrativeStateManager SHALL remain identical across all chapter
    state snapshots.  The initial adversary relationship SHALL also be
    preserved in every snapshot unless explicitly changed.
    """

    @given(
        protagonist=_name_strategy,
        antagonist=_name_strategy.filter(lambda n: True),  # distinct check below
        setting=_setting_strategy,
        chapter_count=_chapter_count_strategy,
        events_per_chapter=st.lists(
            _events_strategy,
            min_size=2,
            max_size=20,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_character_names_consistent_across_chapters(
        self,
        protagonist,
        antagonist,
        setting,
        chapter_count,
        events_per_chapter,
    ):
        """
        **Validates: Requirements 8.9**

        Property: For any multi-chapter book, the protagonist and antagonist
        names stored in the NarrativeStateManager SHALL remain identical in
        every chapter state snapshot produced by advance_chapter().

        The test:
          1. Creates a NarrativeStateManager with the given protagonist,
             antagonist, setting, and chapter_count.
          2. Advances through min(chapter_count, len(events_per_chapter))
             chapters, recording a snapshot after each advance.
          3. Verifies that the character_name field in every snapshot equals
             the original name passed to the constructor.
        """
        # Ensure protagonist and antagonist are distinct to avoid ambiguity
        if protagonist == antagonist:
            antagonist = antagonist + "X"

        # Clamp the number of chapters we actually advance to what was generated
        chapters_to_advance = min(chapter_count, len(events_per_chapter))
        if chapters_to_advance < 1:
            # Nothing to test with zero chapters; skip gracefully
            return

        manager = NarrativeStateManager(
            protagonist=protagonist,
            antagonist=antagonist,
            setting=setting,
            chapter_count=chapter_count,
        )

        # Advance through each chapter
        for i, events in enumerate(events_per_chapter[:chapters_to_advance], start=1):
            manager.advance_chapter(chapter_num=i, events=events)

        # ------------------------------------------------------------------ #
        # Assertion 1: protagonist name is consistent in every snapshot       #
        # ------------------------------------------------------------------ #
        protagonist_history = manager._character_arc_history.get(protagonist, [])
        self.assertGreater(
            len(protagonist_history),
            0,
            f"Expected history for protagonist '{protagonist}' but found none.",
        )
        for idx, snapshot in enumerate(protagonist_history):
            self.assertEqual(
                snapshot.character_name,
                protagonist,
                f"Protagonist name changed at history index {idx}: "
                f"expected '{protagonist}', got '{snapshot.character_name}'.",
            )

        # ------------------------------------------------------------------ #
        # Assertion 2: antagonist name is consistent in every snapshot        #
        # ------------------------------------------------------------------ #
        antagonist_history = manager._character_arc_history.get(antagonist, [])
        self.assertGreater(
            len(antagonist_history),
            0,
            f"Expected history for antagonist '{antagonist}' but found none.",
        )
        for idx, snapshot in enumerate(antagonist_history):
            self.assertEqual(
                snapshot.character_name,
                antagonist,
                f"Antagonist name changed at history index {idx}: "
                f"expected '{antagonist}', got '{snapshot.character_name}'.",
            )

        # ------------------------------------------------------------------ #
        # Assertion 3: initial adversary relationship is preserved in every   #
        # snapshot (unless explicitly changed via update_character_relationship)
        # ------------------------------------------------------------------ #
        for idx, snapshot in enumerate(protagonist_history):
            rel = snapshot.relationships.get(antagonist)
            self.assertEqual(
                rel,
                "adversary",
                f"Protagonist→antagonist relationship changed at history index {idx}: "
                f"expected 'adversary', got '{rel}'.",
            )

        for idx, snapshot in enumerate(antagonist_history):
            rel = snapshot.relationships.get(protagonist)
            self.assertEqual(
                rel,
                "adversary",
                f"Antagonist→protagonist relationship changed at history index {idx}: "
                f"expected 'adversary', got '{rel}'.",
            )

    @given(
        protagonist=_name_strategy,
        antagonist=_name_strategy,
        setting=_setting_strategy,
        chapter_count=_chapter_count_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_manager_stores_correct_names_at_construction(
        self,
        protagonist,
        antagonist,
        setting,
        chapter_count,
    ):
        """
        **Validates: Requirements 8.9**

        Property: Immediately after construction (before any chapter is
        advanced), the NarrativeStateManager SHALL store the exact protagonist
        and antagonist names provided, and the initial character state
        snapshots SHALL reflect those names.
        """
        if protagonist == antagonist:
            antagonist = antagonist + "Y"

        manager = NarrativeStateManager(
            protagonist=protagonist,
            antagonist=antagonist,
            setting=setting,
            chapter_count=chapter_count,
        )

        # Top-level attributes
        self.assertEqual(manager.protagonist, protagonist)
        self.assertEqual(manager.antagonist, antagonist)

        # Initial snapshot (index 0) for protagonist
        p_history = manager._character_arc_history.get(protagonist, [])
        self.assertTrue(
            len(p_history) >= 1,
            f"Expected at least one initial snapshot for protagonist '{protagonist}'.",
        )
        self.assertEqual(p_history[0].character_name, protagonist)

        # Initial snapshot (index 0) for antagonist
        a_history = manager._character_arc_history.get(antagonist, [])
        self.assertTrue(
            len(a_history) >= 1,
            f"Expected at least one initial snapshot for antagonist '{antagonist}'.",
        )
        self.assertEqual(a_history[0].character_name, antagonist)


if __name__ == "__main__":
    unittest.main()

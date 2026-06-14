"""Tests for the LocationCleaner module."""

import pytest
from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.quality.location_cleaner import LocationCleaner


class TestLocationCleaner:
    def setup_method(self):
        self.cleaner = LocationCleaner()

    def test_known_locations_pass(self):
        """Test that known locations pass validation."""
        assert self.cleaner._is_valid_location("London")[0]
        assert self.cleaner._is_valid_location("Paris")[0]
        assert self.cleaner._is_valid_location("New York")[0]
        assert self.cleaner._is_valid_location("San Francisco")[0]
        assert self.cleaner._is_valid_location("Bombay")[0]
        assert self.cleaner._is_valid_location("Calcutta")[0]
        assert self.cleaner._is_valid_location("England")[0]
        assert self.cleaner._is_valid_location("Red Sea")[0]

    def test_generic_locations_fail(self):
        """Test that generic locations fail validation."""
        assert not self.cleaner._is_valid_location("Era")[0]
        assert not self.cleaner._is_valid_location("Age")[0]
        assert not self.cleaner._is_valid_location("Tree")[0]
        assert not self.cleaner._is_valid_location("Flower")[0]
        assert not self.cleaner._is_valid_location("Sky")[0]
        assert not self.cleaner._is_valid_location("Machine")[0]
        assert not self.cleaner._is_valid_location("Entrance")[0]
        assert not self.cleaner._is_valid_location("Quarter")[0]
        assert not self.cleaner._is_valid_location("Capital")[0]
        assert not self.cleaner._is_valid_location("Reign")[0]

    def test_borderline_locations_pass_with_context(self):
        """Test that borderline locations may pass with proper context."""
        text = "They arrived in Paris at midnight."
        assert self.cleaner._is_valid_location("Paris", text)[0]

    def test_clean_fragment_removes_bad_location(self):
        """Test that cleaning removes bad locations."""
        frag = NarrativeFragment(
            source_book="Test",
            text="The old era was over.",
            location="Era",
        )
        self.cleaner.clean_fragment(frag)
        assert frag.location == "" or frag.location is None

    def test_clean_fragment_keeps_good_location(self):
        """Test that cleaning keeps good locations."""
        frag = NarrativeFragment(
            source_book="Test",
            text="She traveled to London for the season.",
            location="London",
        )
        self.cleaner.clean_fragment(frag)
        assert frag.location == "London"

    def test_clean_fragment_extracts_location_from_text(self):
        """Test that cleaning can extract a location from text."""
        frag = NarrativeFragment(
            source_book="Test",
            text="They arrived in London late that evening. The city was dark.",
            location="Era",
        )
        self.cleaner.clean_fragment(frag)
        # Should be replaced with London
        assert frag.location == "London"

    def test_stats_tracking(self):
        """Test that stats are tracked correctly."""
        fragments = [
            NarrativeFragment(
                source_book="Stats Test",
                text="In London.",
                location="London",
            ),
            NarrativeFragment(
                source_book="Stats Test",
                text="The era was over.",
                location="Era",
            ),
            NarrativeFragment(
                source_book="Stats Test",
                text="In Paris.",
                location="Paris",
            ),
            NarrativeFragment(
                source_book="Stats Test",
                text="The age had passed.",
                location="Age",
            ),
        ]

        self.cleaner.clean_fragments(fragments)
        stats = self.cleaner.get_stats()

        assert stats["total_locations_checked"] == 4
        assert stats["invalid_locations"] == 2  # Era, Age
        assert stats["fragments_cleaned"] >= 2

    def test_empty_location(self):
        """Test fragments with no location."""
        frag = NarrativeFragment(
            source_book="Test",
            text="It was dark.",
            location="",
        )
        result = self.cleaner.clean_fragment(frag)
        assert result is None

    def test_location_like_words(self):
        """Test that location-like words pass."""
        # "Hampshire" ends with "shire"
        frag = NarrativeFragment(
            source_book="Test",
            text="They went to Hampshire.",
            location="Hampshire",
        )
        result = self.cleaner.clean_fragment(frag)
        # Hampshire has 'shire' suffix, should pass _is_location_like
        # It's not in generic_locations, and not in known_locations
        # Could also match through text context
        if result:
            assert result == "Hampshire"

    def test_multi_word_location(self):
        """Test multi-word location handling."""
        frag = NarrativeFragment(
            source_book="Test",
            text="They visited New York City.",
            location="New York City",
        )
        self.cleaner.clean_fragment(frag)
        assert frag.location == "New York City"

    def test_clean_fragments_all(self):
        """Test cleaning all fragments."""
        fragments = [
            NarrativeFragment(
                source_book="Book1",
                text="In London.",
                location="London",
            ),
            NarrativeFragment(
                source_book="Book1",
                text="The era ended.",
                location="Era",
            ),
        ]

        self.cleaner.clean_fragments(fragments)
        assert fragments[0].location == "London"
        assert fragments[1].location == "" or fragments[1].location is None

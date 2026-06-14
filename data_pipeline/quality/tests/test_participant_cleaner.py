"""Tests for the ParticipantCleaner module."""

import pytest
from data_pipeline.schema.fragment import NarrativeFragment
from data_pipeline.quality.participant_cleaner import ParticipantCleaner


class TestParticipantCleaner:
    def setup_method(self):
        self.cleaner = ParticipantCleaner()

    def test_valid_character_name(self):
        """Test that valid character names pass validation."""
        assert self.cleaner._is_valid_character_name("Elizabeth")
        assert self.cleaner._is_valid_character_name("John")
        assert self.cleaner._is_valid_character_name("Jean Passepartout")
        assert self.cleaner._is_valid_character_name("Phileas Fogg")
        assert self.cleaner._is_valid_character_name("Artagnan")
        assert self.cleaner._is_valid_character_name("Marilla")
        assert self.cleaner._is_valid_character_name("Monsieur Fix")
        assert self.cleaner._is_valid_character_name("Sir Francis")

    def test_invalid_stop_words(self):
        """Test that stop words are rejected."""
        assert not self.cleaner._is_valid_character_name("The")
        assert not self.cleaner._is_valid_character_name("This")
        assert not self.cleaner._is_valid_character_name("What")
        assert not self.cleaner._is_valid_character_name("Where")
        assert not self.cleaner._is_valid_character_name("Then")
        assert not self.cleaner._is_valid_character_name("Now")
        assert not self.cleaner._is_valid_character_name("Yes")
        assert not self.cleaner._is_valid_character_name("Well")
        assert not self.cleaner._is_valid_character_name("Oh")
        assert not self.cleaner._is_valid_character_name("Ah")

    def test_invalid_time_words(self):
        """Test that time-related words are rejected."""
        assert not self.cleaner._is_valid_character_name("November")
        assert not self.cleaner._is_valid_character_name("January")
        assert not self.cleaner._is_valid_character_name("Monday")
        assert not self.cleaner._is_valid_character_name("Summer")
        assert not self.cleaner._is_valid_character_name("Morning")

    def test_invalid_common_verbs(self):
        """Test that common verb forms are rejected."""
        assert not self.cleaner._is_valid_character_name("Said")
        assert not self.cleaner._is_valid_character_name("Come")
        assert not self.cleaner._is_valid_character_name("Look")
        assert not self.cleaner._is_valid_character_name("Find")
        assert not self.cleaner._is_valid_character_name("Tell")

    def test_invalid_prepositions(self):
        """Test that prepositions are rejected."""
        assert not self.cleaner._is_valid_character_name("From")
        assert not self.cleaner._is_valid_character_name("About")
        assert not self.cleaner._is_valid_character_name("Into")
        assert not self.cleaner._is_valid_character_name("Upon")
        assert not self.cleaner._is_valid_character_name("Between")

    def test_invalid_quantifiers(self):
        """Test that quantifiers are rejected."""
        assert not self.cleaner._is_valid_character_name("One")
        assert not self.cleaner._is_valid_character_name("Two")
        assert not self.cleaner._is_valid_character_name("All")
        assert not self.cleaner._is_valid_character_name("Many")
        assert not self.cleaner._is_valid_character_name("Some")

    def test_invalid_locations(self):
        """Test that location words are not treated as character names."""
        assert not self.cleaner._is_valid_character_name("London")
        assert not self.cleaner._is_valid_character_name("Paris")
        assert not self.cleaner._is_valid_character_name("Bombay")

    def test_clean_fragment_removes_garbage(self):
        """Test that cleaning removes garbage participants."""
        frag = NarrativeFragment(
            source_book="Around the World in 80 Days",
            text="The man stood in London and said yes to everything.",
            participants=[
                "Phileas Fogg", "Passepartout", "Fix", "London",
                "Yes", "Now", "Well", "The", "One",
            ],
        )

        self.cleaner.load_known_characters([frag])
        self.cleaner.clean_fragment(frag)

        # Should keep real character names
        assert "Phileas Fogg" in frag.participants
        assert "Passepartout" in frag.participants
        assert "Fix" in frag.participants

        # Should remove garbage
        assert "London" not in frag.participants
        assert "Yes" not in frag.participants
        assert "Now" not in frag.participants
        assert "Well" not in frag.participants
        assert "The" not in frag.participants
        assert "One" not in frag.participants

    def test_clean_multiple_fragments(self):
        """Test cleaning across multiple fragments."""
        fragments = [
            NarrativeFragment(
                source_book="Test Book",
                text="Elizabeth walked with Darcy.",
                participants=["Elizabeth", "Darcy", "The", "Now"],
            ),
            NarrativeFragment(
                source_book="Test Book",
                text="Darcy spoke to Elizabeth.",
                participants=["Darcy", "Elizabeth", "Yes", "Well"],
            ),
        ]

        self.cleaner.load_known_characters(fragments)
        self.cleaner.clean_fragments(fragments)

        for frag in fragments:
            assert "Elizabeth" in frag.participants
            assert "Darcy" in frag.participants
            assert "The" not in frag.participants
            assert "Now" not in frag.participants
            assert "Yes" not in frag.participants
            assert "Well" not in frag.participants

    def test_sentence_start_only_name(self):
        """Test that words only appearing at sentence start are flagged."""
        frag = NarrativeFragment(
            source_book="Test",
            text="The man walked. The dog followed. The sun shone.",
            participants=["The", "Dog", "Sun"],
        )
        self.cleaner.load_known_characters([frag])
        self.cleaner.clean_fragment(frag)

        assert "The" not in frag.participants

    def test_stats_tracking(self):
        """Test that stats are tracked correctly."""
        fragments = [
            NarrativeFragment(
                source_book="Stats Test",
                text="Hello world.",
                participants=["Alice", "Bob", "Yes", "No", "The"],
            ),
        ]

        self.cleaner.clean_fragments(fragments)

        stats = self.cleaner.get_stats()
        assert stats["total_participants_checked"] == 5
        assert stats["invalid_removed"] == 3  # Yes, No, The
        assert stats["fragments_cleaned"] == 1
        assert stats["fragments_seen"] == 1

    def test_empty_participants(self):
        """Test fragments with no participants."""
        frag = NarrativeFragment(
            source_book="Test",
            text="It was a dark and stormy night.",
            participants=[],
        )
        self.cleaner.clean_fragment(frag)
        assert frag.participants == []

    def test_short_names(self):
        """Test that short valid names are kept."""
        frag = NarrativeFragment(
            source_book="Test",
            text="Jo went to the market. Jo bought eggs.",
            participants=["Jo", "Meg", "Amy", "Beth"],
        )
        self.cleaner.load_known_characters([frag])
        self.cleaner.clean_fragment(frag)
        assert "Jo" in frag.participants

    def test_multi_word_valid_names(self):
        """Test that multi-word character names are kept."""
        frag = NarrativeFragment(
            source_book="Test",
            text="Monte Cristo emerged from the shadows.",
            participants=["Monte Cristo"],
        )
        self.cleaner.load_known_characters([frag])
        self.cleaner.clean_fragment(frag)
        assert "Monte Cristo" in frag.participants

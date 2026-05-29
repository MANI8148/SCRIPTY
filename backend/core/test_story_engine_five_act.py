"""
Property-based tests for SHORT story generation (Tasks 7.3 and 7.4)

Tests cover:
- Property 8: SHORT story five-act structure
  Validates: Requirements 24.1
  For any generated SHORT story, the narrative SHALL contain exactly 5 paragraphs
  corresponding to the 5-act structure (introduction, conflict, escalation, climax, resolution).

- Property 9: SHORT story sentence count bounds
  Validates: Requirements 24.6
  For any generated SHORT story, the total sentence count SHALL be between 25 and 60
  sentences inclusive.
"""
import asyncio
import unittest
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.core.story_engine import StoryEngine
from backend.core.data_models import StoryMode


def _make_story_engine():
    """Return a StoryEngine with mocked cache layer for testing."""
    with patch("backend.cache.cache_layer.CacheLayer._connect_redis"):
        from backend.cache.cache_layer import CacheLayer
        
        cache = CacheLayer(redis_url="redis://localhost:9999/0", fallback_to_memory=True)
        cache._redis_available = False
        cache._redis = None
        
        engine = StoryEngine(cache_layer=cache)
        return engine


class TestShortStoryFiveActStructure(unittest.TestCase):
    """
    Property 8: SHORT story five-act structure

    **Validates: Requirements 24.1**

    FOR ALL generated SHORT stories, the narrative SHALL contain exactly 5 paragraphs
    corresponding to the 5-act structure:
      1. Introduction
      2. Conflict
      3. Escalation
      4. Climax
      5. Resolution
    """

    @given(
        location=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"),
                whitelist_characters=" ",
            ),
            min_size=3,
            max_size=50,
        ).filter(lambda x: x.strip() and not x.isspace()),
        year=st.integers(min_value=1800, max_value=2024),
        location_type=st.sampled_from(["urban", "rural", "metro", "coastal", "mountain"]),
    )
    @settings(max_examples=10, deadline=None)
    def test_short_story_has_exactly_five_paragraphs(self, location, year, location_type):
        """
        **Validates: Requirements 24.1**

        Property: For any valid location, year, and location_type, generating a
        SHORT story SHALL produce exactly 5 paragraphs corresponding to the
        5-act structure.

        The test:
          1. Generates a SHORT story with the given parameters
          2. Counts the number of paragraphs (separated by double newlines)
          3. Verifies that exactly 5 paragraphs are present
        """
        engine = _make_story_engine()

        # Generate SHORT story asynchronously
        result = asyncio.run(
            engine.generate_story(
                location_name=location,
                year=year,
                story_mode=StoryMode.SHORT,
                location_type=location_type
            )
        )

        # Extract the story text
        story_text = result.get("story_text", "")
        self.assertIsNotNone(
            story_text,
            f"Story text should not be None for location={location!r}, year={year}"
        )
        self.assertGreater(
            len(story_text),
            0,
            f"Story text should not be empty for location={location!r}, year={year}"
        )

        # Count paragraphs by splitting on double newlines
        # The 5-act structure uses "\n\n" to separate paragraphs
        paragraphs = [p.strip() for p in story_text.split("\n\n") if p.strip()]
        
        self.assertEqual(
            len(paragraphs),
            5,
            f"SHORT story should have exactly 5 paragraphs (5-act structure), "
            f"but got {len(paragraphs)} paragraphs for location={location!r}, "
            f"year={year}, location_type={location_type!r}. "
            f"Paragraphs: {[p[:50] + '...' if len(p) > 50 else p for p in paragraphs]}"
        )

        # Additional validation: verify paragraph_count in result metadata
        paragraph_count = result.get("paragraph_count", 0)
        self.assertEqual(
            paragraph_count,
            5,
            f"Result metadata should report 5 paragraphs, but got {paragraph_count} "
            f"for location={location!r}, year={year}"
        )


class TestShortStorySentenceCount(unittest.TestCase):
    """
    Property 9: SHORT story sentence count bounds

    **Validates: Requirements 24.6**

    FOR ALL generated SHORT stories, the total sentence count SHALL be between
    25 and 60 sentences inclusive.
    """

    @given(
        location=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"),
                whitelist_characters=" ",
            ),
            min_size=3,
            max_size=50,
        ).filter(lambda x: x.strip() and not x.isspace()),
        year=st.integers(min_value=1800, max_value=2024),
        location_type=st.sampled_from(["urban", "rural", "metro", "coastal", "mountain"]),
    )
    @settings(max_examples=10, deadline=None)
    def test_short_story_sentence_count_within_bounds(self, location, year, location_type):
        """
        **Validates: Requirements 24.6**

        Property: For any valid location, year, and location_type, generating a
        SHORT story SHALL produce between 25 and 60 sentences inclusive.

        The test:
          1. Generates a SHORT story with the given parameters
          2. Counts the number of sentences in the story
          3. Verifies that the sentence count is within [25, 60]
        """
        engine = _make_story_engine()

        # Generate SHORT story asynchronously
        result = asyncio.run(
            engine.generate_story(
                location_name=location,
                year=year,
                story_mode=StoryMode.SHORT,
                location_type=location_type
            )
        )

        # Extract the story text
        story_text = result.get("story_text", "")
        self.assertIsNotNone(
            story_text,
            f"Story text should not be None for location={location!r}, year={year}"
        )
        self.assertGreater(
            len(story_text),
            0,
            f"Story text should not be empty for location={location!r}, year={year}"
        )

        # Count sentences by splitting on sentence-ending punctuation
        # A sentence ends with '.', '!', or '?' followed by space or end of string
        import re
        # Split on sentence boundaries: period, exclamation, or question mark
        # followed by whitespace or end of string
        sentences = re.split(r'[.!?]+(?:\s+|$)', story_text)
        # Filter out empty strings and whitespace-only strings
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)
        
        self.assertGreaterEqual(
            sentence_count,
            25,
            f"SHORT story should have at least 25 sentences, "
            f"but got {sentence_count} sentences for location={location!r}, "
            f"year={year}, location_type={location_type!r}. "
            f"Story preview: {story_text[:200]}..."
        )
        
        self.assertLessEqual(
            sentence_count,
            60,
            f"SHORT story should have at most 60 sentences, "
            f"but got {sentence_count} sentences for location={location!r}, "
            f"year={year}, location_type={location_type!r}. "
            f"Story preview: {story_text[:200]}..."
        )


if __name__ == "__main__":
    unittest.main()


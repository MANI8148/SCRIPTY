"""
Property-based test for chapter length variation (Task 9.4)

Tests cover:
- Property 6: Chapter length natural variation
  Validates: Requirements 9.2
  For any generated chapter, the word count SHALL vary within ±20% of the target
  length (2000-4000 words), creating natural pacing variation.
"""
import unittest
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.core.chapter_generator import ChapterGenerator
from backend.core.scene_builder import SceneBuilder


class TestChapterLengthVariation(unittest.TestCase):
    """
    Property 6: Chapter length natural variation

    **Validates: Requirements 9.2**

    FOR ALL generated chapters, the word count SHALL be within the range of
    2000-4000 words, which represents ±20% variation around a 3000-word target.
    This creates natural pacing variation across chapters.
    """

    @given(
        chapter_num=st.integers(min_value=1, max_value=20),
        total_chapters=st.integers(min_value=10, max_value=20),
        location=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"),
                whitelist_characters=" ",
            ),
            min_size=3,
            max_size=50,
        ).filter(lambda x: x.strip() and not x.isspace()),
        protagonist=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"),
                whitelist_characters=" ",
            ),
            min_size=3,
            max_size=30,
        ).filter(lambda x: x.strip() and not x.isspace()),
        year=st.integers(min_value=1800, max_value=2024),
    )
    @settings(max_examples=100, deadline=None)
    def test_chapter_word_count_within_target_range(
        self, chapter_num, total_chapters, location, protagonist, year
    ):
        """
        **Validates: Requirements 9.2**

        Property: For any valid chapter parameters, generating a chapter SHALL
        produce a word count within the range of 2000-4000 words.

        The test:
          1. Generates a chapter with the given parameters
          2. Counts the total words in the chapter (sum of all scene word counts)
          3. Verifies that the word count is within [2000, 4000]

        The range 2000-4000 represents ±20% variation around a 3000-word target:
        - Lower bound: 3000 - (3000 * 0.33) ≈ 2000
        - Upper bound: 3000 + (3000 * 0.33) ≈ 4000
        """
        # Ensure chapter_num doesn't exceed total_chapters
        if chapter_num > total_chapters:
            chapter_num = total_chapters

        # Create chapter generator with scene builder
        scene_builder = SceneBuilder()
        chapter_generator = ChapterGenerator(scene_builder=scene_builder)

        # Create context for chapter generation
        context = {
            "location": location,
            "protagonist": protagonist,
            "antagonist": "the antagonist",
            "obj": "the artifact",
            "role": "detective",
            "year": year,
            "total_chapters": total_chapters,
        }

        # Generate chapter
        chapter = chapter_generator.generate_chapter(
            chapter_num=chapter_num, context=context
        )

        # Verify chapter was generated
        self.assertIsNotNone(
            chapter,
            f"Chapter should not be None for chapter_num={chapter_num}, "
            f"total_chapters={total_chapters}",
        )

        # Get word count from chapter
        word_count = chapter.word_count

        # Verify word count is within target range [2000, 4000]
        self.assertGreaterEqual(
            word_count,
            2000,
            f"Chapter word count should be at least 2000 words, "
            f"but got {word_count} words for chapter_num={chapter_num}, "
            f"total_chapters={total_chapters}, location={location!r}. "
            f"Chapter has {len(chapter.scenes)} scenes.",
        )

        self.assertLessEqual(
            word_count,
            4000,
            f"Chapter word count should be at most 4000 words, "
            f"but got {word_count} words for chapter_num={chapter_num}, "
            f"total_chapters={total_chapters}, location={location!r}. "
            f"Chapter has {len(chapter.scenes)} scenes.",
        )

        # Additional validation: verify word count matches sum of scene word counts
        calculated_word_count = sum(scene.word_count for scene in chapter.scenes)
        self.assertEqual(
            word_count,
            calculated_word_count,
            f"Chapter word_count ({word_count}) should match sum of scene word counts "
            f"({calculated_word_count}) for chapter_num={chapter_num}",
        )


if __name__ == "__main__":
    unittest.main()

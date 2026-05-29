"""
Property-based test for scene type alternation (Task 9.5)

Tests cover:
- Property 7: Scene type alternation
  Validates: Requirements 12.2
  For any generated chapter, there SHALL NOT be more than 2 consecutive scenes
  of the same type, ensuring narrative variety.
"""
import unittest

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.core.chapter_generator import ChapterGenerator
from backend.core.scene_builder import SceneBuilder


class TestSceneTypeAlternation(unittest.TestCase):
    """
    Property 7: Scene type alternation

    **Validates: Requirements 12.2**

    FOR ALL generated chapters, no more than 2 consecutive scenes SHALL share
    the same scene type. This ensures narrative variety and prevents monotonous
    repetition of action, dialogue, introspection, description, or transition
    scenes within a single chapter.
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
    def test_no_more_than_two_consecutive_scenes_of_same_type(
        self, chapter_num, total_chapters, location, protagonist, year
    ):
        """
        **Validates: Requirements 12.2**

        Property: For any valid chapter parameters, generating a chapter SHALL
        produce a scene sequence where no more than 2 consecutive scenes share
        the same scene type.

        The test:
          1. Generates a chapter with the given parameters
          2. Extracts the scene type sequence from the generated scenes
          3. Checks every run of consecutive identical scene types
          4. Verifies that no run exceeds length 2
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

        # Verify chapter was generated with at least one scene
        self.assertIsNotNone(
            chapter,
            f"Chapter should not be None for chapter_num={chapter_num}, "
            f"total_chapters={total_chapters}",
        )
        self.assertGreater(
            len(chapter.scenes),
            0,
            f"Chapter should have at least one scene for chapter_num={chapter_num}",
        )

        # Extract scene type sequence
        scene_types = [scene.scene_type for scene in chapter.scenes]
        type_names = [st.value for st in scene_types]

        # Check that no more than 2 consecutive scenes share the same type.
        # Walk through the sequence and track the current run length.
        max_run = 1
        current_run = 1
        for i in range(1, len(scene_types)):
            if scene_types[i] == scene_types[i - 1]:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 1

        self.assertLessEqual(
            max_run,
            2,
            f"No more than 2 consecutive scenes should share the same type, "
            f"but found a run of {max_run} consecutive scenes of the same type. "
            f"Scene type sequence: {type_names}. "
            f"chapter_num={chapter_num}, total_chapters={total_chapters}, "
            f"location={location!r}, year={year}.",
        )


if __name__ == "__main__":
    unittest.main()

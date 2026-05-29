"""
Integration tests for BOOK generation (Task 12.4)

Tests cover:
- End-to-end 10-chapter book generation
- Character consistency across all chapters
- Plot thread resolution by the final chapter
- Generation time meets target (<30s for 10 chapters)

Requirements: 7.3, 8.2, 8.4, 8.7, 8.8, 8.9, 11.4, 14.1, 14.2, 14.3, 14.4
"""
import asyncio
import time
import unittest

from backend.core.story_engine import StoryEngine
from backend.core.data_models import StoryMode, Chapter, Scene, SceneType, BookMetadata
from backend.core.narrative_state_manager import NarrativeStateManager
from backend.core.chapter_generator import ChapterGenerator
from backend.cache.cache_layer import CacheLayer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_async(coro):
    """Run a coroutine synchronously in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def generate_book(chapter_count: int = 10, location: str = "Mumbai", year: int = 1950) -> dict:
    """
    Generate a BOOK directly via _generate_book (bypasses job queue for
    synchronous testing).
    """
    engine = StoryEngine()
    # Build a minimal context that _generate_book expects
    context = {
        "location": location,
        "year": year,
        "loc_data": {"description": "a historic city of great significance"},
        "time": {"era": "modern", "period": "post-independence"},
        "genre": "Historical Fiction",
        "theme": "justice",
    }
    return run_async(engine._generate_book(context, chapter_count))


# ---------------------------------------------------------------------------
# 1. End-to-end 10-chapter book generation
# ---------------------------------------------------------------------------

class TestBookGenerationEndToEnd(unittest.TestCase):
    """
    Verify that a 10-chapter book is generated with the correct structure.

    Requirements: 8.2, 8.4, 14.1, 14.2, 14.3, 14.4
    """

    @classmethod
    def setUpClass(cls):
        """Generate the book once and share across all tests in this class."""
        cls.result = generate_book(chapter_count=10)

    # --- Top-level structure ---

    def test_result_has_story_mode_book(self):
        self.assertEqual(self.result["story_mode"], "book")

    def test_result_has_chapters_key(self):
        self.assertIn("chapters", self.result)

    def test_result_has_exactly_10_chapters(self):
        self.assertEqual(len(self.result["chapters"]), 10)

    def test_chapter_count_field_is_10(self):
        self.assertEqual(self.result["chapter_count"], 10)

    # --- Prologue ---

    def test_prologue_present(self):
        self.assertIn("prologue", self.result)
        self.assertIsInstance(self.result["prologue"], str)
        self.assertGreater(len(self.result["prologue"].strip()), 0)

    def test_prologue_mentions_location(self):
        self.assertIn("Mumbai", self.result["prologue"])

    # --- Epilogue ---

    def test_epilogue_present(self):
        self.assertIn("epilogue", self.result)
        self.assertIsInstance(self.result["epilogue"], str)
        self.assertGreater(len(self.result["epilogue"].strip()), 0)

    def test_epilogue_mentions_location(self):
        self.assertIn("Mumbai", self.result["epilogue"])

    # --- Chapters ---

    def test_chapters_are_chapter_objects(self):
        for ch in self.result["chapters"]:
            self.assertIsInstance(ch, Chapter)

    def test_chapters_numbered_1_to_10(self):
        nums = [ch.chapter_num for ch in self.result["chapters"]]
        self.assertEqual(nums, list(range(1, 11)))

    def test_each_chapter_has_title(self):
        for ch in self.result["chapters"]:
            self.assertIsInstance(ch.title, str)
            self.assertGreater(len(ch.title.strip()), 0)

    def test_each_chapter_has_scenes(self):
        for ch in self.result["chapters"]:
            self.assertIsInstance(ch.scenes, list)
            self.assertGreater(len(ch.scenes), 0)

    def test_each_chapter_has_summary(self):
        for ch in self.result["chapters"]:
            self.assertIsInstance(ch.summary, str)
            self.assertGreater(len(ch.summary.strip()), 0)

    def test_each_chapter_has_positive_word_count(self):
        for ch in self.result["chapters"]:
            self.assertGreater(ch.word_count, 0)

    def test_each_chapter_meets_minimum_word_count(self):
        """Each chapter must have at least 2000 words (Requirement 8.5)."""
        for ch in self.result["chapters"]:
            self.assertGreaterEqual(
                ch.word_count,
                2000,
                f"Chapter {ch.chapter_num} has only {ch.word_count} words (min 2000).",
            )

    def test_each_chapter_within_maximum_word_count(self):
        """Each chapter must not exceed 4000 words (Requirement 8.5)."""
        for ch in self.result["chapters"]:
            self.assertLessEqual(
                ch.word_count,
                4000,
                f"Chapter {ch.chapter_num} has {ch.word_count} words (max 4000).",
            )

    def test_each_scene_has_content(self):
        for ch in self.result["chapters"]:
            for sc in ch.scenes:
                self.assertIsInstance(sc.content, str)
                self.assertGreater(len(sc.content.strip()), 0)

    def test_each_scene_has_valid_type(self):
        valid_types = set(SceneType)
        for ch in self.result["chapters"]:
            for sc in ch.scenes:
                self.assertIn(sc.scene_type, valid_types)

    def test_each_scene_has_positive_word_count(self):
        for ch in self.result["chapters"]:
            for sc in ch.scenes:
                self.assertGreater(sc.word_count, 0)

    # --- Metadata ---

    def test_metadata_present(self):
        self.assertIn("metadata", self.result)
        self.assertIsInstance(self.result["metadata"], BookMetadata)

    def test_metadata_chapter_count_is_10(self):
        self.assertEqual(self.result["metadata"].chapter_count, 10)

    def test_metadata_total_word_count_positive(self):
        self.assertGreater(self.result["metadata"].total_word_count, 0)

    def test_metadata_reading_time_positive(self):
        self.assertGreater(self.result["metadata"].reading_time_minutes, 0)

    def test_metadata_has_title(self):
        self.assertIsInstance(self.result["metadata"].title, str)
        self.assertGreater(len(self.result["metadata"].title.strip()), 0)

    def test_metadata_has_author_attribution(self):
        self.assertIsInstance(self.result["metadata"].author_attribution, str)
        self.assertGreater(len(self.result["metadata"].author_attribution.strip()), 0)

    def test_metadata_has_genre(self):
        self.assertIsInstance(self.result["metadata"].genre, str)
        self.assertGreater(len(self.result["metadata"].genre.strip()), 0)

    def test_metadata_has_scene_count(self):
        self.assertGreater(self.result["metadata"].scene_count, 0)

    def test_metadata_scene_count_matches_actual(self):
        actual_scenes = sum(len(ch.scenes) for ch in self.result["chapters"])
        self.assertEqual(self.result["metadata"].scene_count, actual_scenes)

    # --- Table of contents ---

    def test_table_of_contents_present(self):
        self.assertIn("table_of_contents", self.result)
        self.assertIsInstance(self.result["table_of_contents"], list)

    def test_table_of_contents_includes_prologue(self):
        titles = [title for _, title in self.result["table_of_contents"]]
        self.assertIn("Prologue", titles)

    def test_table_of_contents_includes_epilogue(self):
        titles = [title for _, title in self.result["table_of_contents"]]
        self.assertIn("Epilogue", titles)

    def test_table_of_contents_includes_all_chapters(self):
        toc_titles = [title for _, title in self.result["table_of_contents"]]
        for ch in self.result["chapters"]:
            self.assertIn(ch.title, toc_titles)

    # --- Word count ---

    def test_total_word_count_substantial(self):
        """A 10-chapter book should have at least 20,000 words."""
        self.assertGreater(
            self.result["word_count"],
            20000,
            f"Expected >20,000 words, got {self.result['word_count']}.",
        )

    def test_word_count_field_matches_metadata(self):
        self.assertEqual(self.result["word_count"], self.result["metadata"].total_word_count)


# ---------------------------------------------------------------------------
# 2. Character consistency across all chapters
# ---------------------------------------------------------------------------

class TestCharacterConsistencyAcrossChapters(unittest.TestCase):
    """
    Verify that protagonist and antagonist names remain consistent across
    all chapters in the generated book.

    Requirements: 8.9, 10.1
    """

    @classmethod
    def setUpClass(cls):
        cls.result = generate_book(chapter_count=10)
        # Extract character names from the engine state via the prologue/epilogue
        # (the names appear in both)
        cls.prologue = cls.result["prologue"]
        cls.epilogue = cls.result["epilogue"]
        cls.chapters = cls.result["chapters"]

    def _extract_names_from_text(self, text: str) -> set:
        """
        Extract capitalised words (potential character names) from text.
        Returns a set of candidate names.
        """
        words = text.split()
        return {w.strip(".,;:!?\"'()") for w in words if w and w[0].isupper() and len(w) > 2}

    def test_prologue_and_epilogue_share_character_names(self):
        """
        The same protagonist and antagonist names that appear in the prologue
        should also appear in the epilogue.
        """
        prologue_names = self._extract_names_from_text(self.prologue)
        epilogue_names = self._extract_names_from_text(self.epilogue)
        # There should be at least some overlap (shared character names)
        overlap = prologue_names & epilogue_names
        self.assertGreater(
            len(overlap),
            0,
            "No shared names found between prologue and epilogue — "
            "character names may not be consistent.",
        )

    def test_chapter_titles_do_not_contradict_each_other(self):
        """All chapter titles should be non-empty and unique."""
        titles = [ch.title for ch in self.chapters]
        self.assertEqual(len(titles), len(set(titles)), "Duplicate chapter titles found.")

    def test_chapter_summaries_are_non_empty(self):
        for ch in self.chapters:
            self.assertGreater(
                len(ch.summary.strip()),
                0,
                f"Chapter {ch.chapter_num} has an empty summary.",
            )

    def test_narrative_state_manager_character_consistency(self):
        """
        Directly test NarrativeStateManager: character names must remain
        identical across all chapter snapshots.
        """
        protagonist = "Arjun"
        antagonist = "Vikram"
        setting = {"location": "Mumbai", "year": 1950}
        chapter_count = 10

        manager = NarrativeStateManager(
            protagonist=protagonist,
            antagonist=antagonist,
            setting=setting,
            chapter_count=chapter_count,
        )
        manager.initialize_character_arcs()
        manager.initialize_plot_threads()

        # Advance through all 10 chapters
        for i in range(1, chapter_count + 1):
            manager.advance_chapter(i, [f"Chapter {i} event occurred."])

        # Verify protagonist name is consistent in every snapshot
        p_history = manager._character_arc_history[protagonist]
        for idx, snapshot in enumerate(p_history):
            self.assertEqual(
                snapshot.character_name,
                protagonist,
                f"Protagonist name changed at snapshot {idx}: "
                f"expected '{protagonist}', got '{snapshot.character_name}'.",
            )

        # Verify antagonist name is consistent in every snapshot
        a_history = manager._character_arc_history[antagonist]
        for idx, snapshot in enumerate(a_history):
            self.assertEqual(
                snapshot.character_name,
                antagonist,
                f"Antagonist name changed at snapshot {idx}: "
                f"expected '{antagonist}', got '{snapshot.character_name}'.",
            )

    def test_character_arc_history_length_matches_chapters(self):
        """
        After advancing N chapters, each character should have N+1 snapshots
        (initial + one per chapter).
        """
        protagonist = "Priya"
        antagonist = "Rajan"
        chapter_count = 10

        manager = NarrativeStateManager(
            protagonist=protagonist,
            antagonist=antagonist,
            setting={"location": "Delhi", "year": 1960},
            chapter_count=chapter_count,
        )
        manager.initialize_character_arcs()
        manager.initialize_plot_threads()

        for i in range(1, chapter_count + 1):
            manager.advance_chapter(i, [f"Event {i}"])

        # initial snapshot + 10 chapter snapshots = 11
        self.assertEqual(len(manager._character_arc_history[protagonist]), chapter_count + 1)
        self.assertEqual(len(manager._character_arc_history[antagonist]), chapter_count + 1)

    def test_adversary_relationship_preserved_across_all_chapters(self):
        """
        The initial adversary relationship between protagonist and antagonist
        must be preserved in every chapter snapshot.
        """
        protagonist = "Meera"
        antagonist = "Shyam"
        chapter_count = 10

        manager = NarrativeStateManager(
            protagonist=protagonist,
            antagonist=antagonist,
            setting={"location": "Kolkata", "year": 1940},
            chapter_count=chapter_count,
        )
        manager.initialize_character_arcs()
        manager.initialize_plot_threads()

        for i in range(1, chapter_count + 1):
            manager.advance_chapter(i, [f"Chapter {i} event"])

        for idx, snapshot in enumerate(manager._character_arc_history[protagonist]):
            rel = snapshot.relationships.get(antagonist)
            self.assertEqual(
                rel,
                "adversary",
                f"Protagonist→antagonist relationship changed at snapshot {idx}: "
                f"expected 'adversary', got '{rel}'.",
            )

    def test_character_state_retrievable_at_each_chapter(self):
        """
        get_character_state() must return a valid state dict for every chapter
        from 0 to chapter_count.
        """
        protagonist = "Kavya"
        antagonist = "Deva"
        chapter_count = 10

        manager = NarrativeStateManager(
            protagonist=protagonist,
            antagonist=antagonist,
            setting={"location": "Chennai", "year": 1970},
            chapter_count=chapter_count,
        )
        manager.initialize_character_arcs()
        manager.initialize_plot_threads()

        for i in range(1, chapter_count + 1):
            manager.advance_chapter(i, [f"Event {i}"])

        for chapter_num in range(0, chapter_count + 1):
            state = manager.get_character_state(protagonist, chapter_num)
            self.assertIsInstance(state, dict)
            self.assertIn("character_name", state)
            self.assertEqual(state["character_name"], protagonist)


# ---------------------------------------------------------------------------
# 3. Plot thread resolution
# ---------------------------------------------------------------------------

class TestPlotThreadResolution(unittest.TestCase):
    """
    Verify that all plot threads are resolved by the final chapter.

    Requirements: 8.8, 11.4
    """

    def _make_manager_and_advance(self, chapter_count: int) -> NarrativeStateManager:
        """Create a manager, initialise threads, and advance all chapters."""
        manager = NarrativeStateManager(
            protagonist="Arjun",
            antagonist="Vikram",
            setting={"location": "Mumbai", "year": 1950},
            chapter_count=chapter_count,
        )
        manager.initialize_character_arcs()
        manager.initialize_plot_threads()
        for i in range(1, chapter_count + 1):
            manager.advance_chapter(i, [f"Chapter {i} event."])
        return manager

    def test_no_unresolved_threads_after_10_chapters(self):
        manager = self._make_manager_and_advance(10)
        unresolved = manager.get_unresolved_threads()
        self.assertEqual(
            unresolved,
            [],
            f"Expected all threads resolved after 10 chapters, "
            f"but found: {[t['thread_id'] for t in unresolved]}",
        )

    def test_no_unresolved_threads_after_15_chapters(self):
        manager = self._make_manager_and_advance(15)
        unresolved = manager.get_unresolved_threads()
        self.assertEqual(
            unresolved,
            [],
            f"Expected all threads resolved after 15 chapters, "
            f"but found: {[t['thread_id'] for t in unresolved]}",
        )

    def test_no_unresolved_threads_after_20_chapters(self):
        manager = self._make_manager_and_advance(20)
        unresolved = manager.get_unresolved_threads()
        self.assertEqual(
            unresolved,
            [],
            f"Expected all threads resolved after 20 chapters, "
            f"but found: {[t['thread_id'] for t in unresolved]}",
        )

    def test_continuity_check_passes_after_10_chapters(self):
        """check_continuity() should return no issues after all chapters complete."""
        manager = self._make_manager_and_advance(10)
        issues = manager.check_continuity()
        self.assertEqual(
            issues,
            [],
            f"Continuity issues found after 10 chapters: {issues}",
        )

    def test_main_plot_thread_resolved_at_final_chapter(self):
        manager = self._make_manager_and_advance(10)
        main_plot = next(
            (t for t in manager.plot_threads if t.thread_type == "main_plot"),
            None,
        )
        self.assertIsNotNone(main_plot, "No main_plot thread found.")
        self.assertEqual(
            main_plot.status,
            "resolved",
            f"Main plot thread not resolved after 10 chapters (status: {main_plot.status}).",
        )

    def test_all_thread_types_resolved(self):
        manager = self._make_manager_and_advance(10)
        for thread in manager.plot_threads:
            self.assertEqual(
                thread.status,
                "resolved",
                f"Thread '{thread.thread_id}' ({thread.thread_type}) "
                f"not resolved after 10 chapters.",
            )

    def test_threads_active_before_resolution_chapter(self):
        """
        Threads should still be active before their resolution chapter.
        """
        manager = NarrativeStateManager(
            protagonist="Arjun",
            antagonist="Vikram",
            setting={"location": "Mumbai", "year": 1950},
            chapter_count=10,
        )
        manager.initialize_character_arcs()
        manager.initialize_plot_threads()

        # Advance only 1 chapter — most threads should still be active
        manager.advance_chapter(1, ["Opening event."])
        active = manager.get_active_plot_threads(1)
        self.assertGreater(
            len(active),
            0,
            "Expected at least one active thread after chapter 1.",
        )

    def test_book_generation_result_has_no_continuity_issues(self):
        """
        The full _generate_book() result should report no continuity issues.
        """
        result = generate_book(chapter_count=10)
        issues = result.get("continuity_issues", [])
        self.assertEqual(
            issues,
            [],
            f"Continuity issues in generated book: {issues}",
        )

    def test_plot_threads_have_foreshadowing_in_earlier_chapters(self):
        """
        Each plot thread should have at least one foreshadowing chapter
        that precedes its resolution chapter.
        """
        manager = NarrativeStateManager(
            protagonist="Arjun",
            antagonist="Vikram",
            setting={"location": "Mumbai", "year": 1950},
            chapter_count=10,
        )
        manager.initialize_plot_threads()

        for thread in manager.plot_threads:
            if thread.resolved_chapter is not None:
                foreshadowing_before_resolution = [
                    ch for ch in thread.foreshadowing_chapters
                    if ch < thread.resolved_chapter
                ]
                self.assertGreater(
                    len(foreshadowing_before_resolution),
                    0,
                    f"Thread '{thread.thread_id}' has no foreshadowing before "
                    f"its resolution chapter {thread.resolved_chapter}.",
                )


# ---------------------------------------------------------------------------
# 4. Generation time target (<30s for 10 chapters)
# ---------------------------------------------------------------------------

class TestBookGenerationTime(unittest.TestCase):
    """
    Verify that 10-chapter book generation completes within 30 seconds.

    Requirements: 7.3
    """

    GENERATION_TIME_LIMIT_SECONDS = 30

    def test_10_chapter_book_generates_within_30_seconds(self):
        """
        End-to-end 10-chapter book generation must complete in under 30 seconds.

        This test calls _generate_book() directly (bypassing the job queue)
        to measure pure generation time without queue overhead.
        """
        start = time.monotonic()
        result = generate_book(chapter_count=10)
        elapsed = time.monotonic() - start

        # Verify the book was actually generated
        self.assertEqual(len(result["chapters"]), 10)

        self.assertLess(
            elapsed,
            self.GENERATION_TIME_LIMIT_SECONDS,
            f"10-chapter book generation took {elapsed:.2f}s, "
            f"exceeding the {self.GENERATION_TIME_LIMIT_SECONDS}s target.",
        )

    def test_generation_time_recorded_correctly(self):
        """
        Verify that the generation produces a complete result (sanity check
        that the timing test is measuring a real generation).
        """
        start = time.monotonic()
        result = generate_book(chapter_count=10)
        elapsed = time.monotonic() - start

        # The result must be a complete book
        self.assertIn("chapters", result)
        self.assertEqual(result["chapter_count"], 10)
        self.assertGreater(result["word_count"], 0)

        # Log the actual time for informational purposes
        print(f"\n[INFO] 10-chapter book generated in {elapsed:.2f}s")

    def test_chapter_generator_performance(self):
        """
        Individual chapter generation should be fast enough to support
        the 30-second total target (i.e., each chapter < 3s on average).
        """
        generator = ChapterGenerator()
        context = {
            "location": "Mumbai",
            "year": 1950,
            "protagonist": "Arjun",
            "antagonist": "Vikram",
            "role": "investigator",
            "role_logic": {
                "specialty": "uncovering hidden truths",
                "action_modifier": "carefully examining",
            },
            "obj": "manuscript",
            "obj_type": "document",
            "action": "decipher",
            "loc_data": {"description": "a historic city"},
            "time": {"era": "modern"},
            "total_chapters": 10,
        }

        total_time = 0.0
        num_chapters = 10
        for chapter_num in range(1, num_chapters + 1):
            start = time.monotonic()
            chapter = generator.generate_chapter(chapter_num=chapter_num, context=context)
            elapsed = time.monotonic() - start
            total_time += elapsed

            # Each chapter should complete in under 5 seconds
            self.assertLess(
                elapsed,
                5.0,
                f"Chapter {chapter_num} took {elapsed:.2f}s (limit: 5s per chapter).",
            )

        # Total for 10 chapters should be under 30 seconds
        self.assertLess(
            total_time,
            self.GENERATION_TIME_LIMIT_SECONDS,
            f"10 chapters took {total_time:.2f}s total (limit: {self.GENERATION_TIME_LIMIT_SECONDS}s).",
        )
        print(f"\n[INFO] 10 chapters generated in {total_time:.2f}s total")


# ---------------------------------------------------------------------------
# 5. Full StoryEngine BOOK mode integration (via generate_story)
# ---------------------------------------------------------------------------

class TestStoryEngineBookMode(unittest.TestCase):
    """
    Integration tests for StoryEngine.generate_story() in BOOK mode.

    These tests use the job queue path (returns job_id) and verify the
    queued response structure.

    Requirements: 8.1, 8.2, 8.4
    """

    def test_generate_story_book_mode_returns_job_id(self):
        """
        generate_story() in BOOK mode should return a job_id immediately
        (async background processing).
        """
        engine = StoryEngine()
        result = run_async(
            engine.generate_story(
                location_name="Mumbai",
                year=1950,
                story_mode=StoryMode.BOOK,
                chapter_count=10,
            )
        )
        self.assertEqual(result["story_mode"], "book")
        self.assertIn("job_id", result)
        self.assertIsInstance(result["job_id"], str)
        self.assertGreater(len(result["job_id"]), 0)

    def test_generate_story_book_mode_status_is_queued(self):
        """
        The initial status returned by generate_story() in BOOK mode
        should be 'queued'.
        """
        engine = StoryEngine()
        result = run_async(
            engine.generate_story(
                location_name="Delhi",
                year=1960,
                story_mode=StoryMode.BOOK,
                chapter_count=10,
            )
        )
        self.assertEqual(result["status"], "queued")

    def test_generate_story_book_mode_job_completes(self):
        """
        After submitting a BOOK job, polling the job queue should eventually
        show a completed status with a full book result.
        """
        engine = StoryEngine()
        result = run_async(
            engine.generate_story(
                location_name="Kolkata",
                year=1900,
                story_mode=StoryMode.BOOK,
                chapter_count=10,
            )
        )
        job_id = result["job_id"]

        # Poll for completion (up to 60 seconds)
        deadline = time.monotonic() + 60
        job_status = None
        while time.monotonic() < deadline:
            job_status = engine.job_queue.get_job_status(job_id)
            if job_status and job_status["status"] in ("completed", "failed", "timeout"):
                break
            time.sleep(1)

        self.assertIsNotNone(job_status, "Job status not found in queue.")
        self.assertEqual(
            job_status["status"],
            "completed",
            f"Job did not complete successfully. Status: {job_status['status']}, "
            f"Error: {job_status.get('error')}",
        )

        # Verify the completed result has the expected structure
        book_result = job_status["result"]
        self.assertIsNotNone(book_result)
        self.assertEqual(book_result["story_mode"], "book")
        self.assertEqual(len(book_result["chapters"]), 10)
        self.assertGreater(book_result["word_count"], 20000)

    def test_generate_story_book_mode_chapter_count_clamped_to_minimum(self):
        """
        chapter_count below 10 should be clamped to 10 (minimum for BOOK mode).
        """
        engine = StoryEngine()
        # Generate directly (bypass job queue) to test clamping
        context = {
            "location": "Pune",
            "year": 1980,
            "loc_data": {"description": "a vibrant city"},
            "time": {"era": "modern"},
            "genre": "Drama",
            "theme": "redemption",
        }
        result = run_async(engine._generate_book(context, chapter_count=5))
        # Should be clamped to 10
        self.assertEqual(result["chapter_count"], 10)
        self.assertEqual(len(result["chapters"]), 10)

    def test_generate_story_book_mode_chapter_count_clamped_to_maximum(self):
        """
        chapter_count above 20 should be clamped to 20 (maximum for BOOK mode).
        """
        engine = StoryEngine()
        context = {
            "location": "Hyderabad",
            "year": 1990,
            "loc_data": {"description": "a city of pearls"},
            "time": {"era": "modern"},
            "genre": "Thriller",
            "theme": "power",
        }
        result = run_async(engine._generate_book(context, chapter_count=25))
        # Should be clamped to 20
        self.assertEqual(result["chapter_count"], 20)
        self.assertEqual(len(result["chapters"]), 20)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)

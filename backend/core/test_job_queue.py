"""
Tests for the background job queue system (task 12.2).

Covers:
- Job submission and status tracking (queued → processing → completed/failed/timeout)
- Progress tracking (chapters_completed, percent_complete)
- 60-second timeout with partial book return
- Thread safety of the job queue

Requirements: 7.3, 16.4
"""
import asyncio
import time
import threading
from unittest.mock import MagicMock, patch

import pytest

try:
    from backend.core.job_queue import (
        BookJobQueue,
        Job,
        JobProgress,
        JobStatus,
        BOOK_GENERATION_TIMEOUT_SECONDS,
        get_job_queue,
    )
except ImportError:
    from core.job_queue import (
        BookJobQueue,
        Job,
        JobProgress,
        JobStatus,
        BOOK_GENERATION_TIMEOUT_SECONDS,
        get_job_queue,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _fast_task(chapter_count: int = 3, progress_callback=None) -> dict:
    """A quick async task that simulates generating a few chapters."""
    chapters = []
    for i in range(1, chapter_count + 1):
        await asyncio.sleep(0.01)  # simulate work
        chapter = {"chapter_num": i, "title": f"Chapter {i}", "word_count": 500}
        chapters.append(chapter)
        if progress_callback:
            progress_callback(i, chapter, {"story_mode": "book"})
    return {
        "story_mode": "book",
        "chapters": chapters,
        "word_count": chapter_count * 500,
    }


async def _failing_task(chapter_count: int = 3, progress_callback=None) -> dict:
    """A task that always raises an exception."""
    raise RuntimeError("Simulated generation failure")


async def _slow_task(chapter_count: int = 3, progress_callback=None) -> dict:
    """A task that sleeps longer than the timeout."""
    await asyncio.sleep(120)  # longer than BOOK_GENERATION_TIMEOUT_SECONDS
    return {"story_mode": "book", "chapters": []}


async def _partial_task(chapter_count: int = 5, progress_callback=None) -> dict:
    """Generates some chapters then sleeps past the timeout."""
    chapters = []
    for i in range(1, 3):  # only generate 2 chapters before sleeping
        await asyncio.sleep(0.01)
        chapter = {"chapter_num": i, "title": f"Chapter {i}", "word_count": 400}
        chapters.append(chapter)
        if progress_callback:
            progress_callback(i, chapter, {"story_mode": "book"})
    # Now sleep past the timeout
    await asyncio.sleep(120)
    return {"story_mode": "book", "chapters": chapters}


# ---------------------------------------------------------------------------
# Unit tests: JobProgress
# ---------------------------------------------------------------------------

class TestJobProgress:
    def test_initial_state(self):
        p = JobProgress()
        assert p.chapters_completed == 0
        assert p.total_chapters == 0
        assert p.percent_complete == 0.0
        assert p.current_chapter is None

    def test_update_progress(self):
        p = JobProgress()
        p.update(3, 10)
        assert p.chapters_completed == 3
        assert p.total_chapters == 10
        assert p.percent_complete == 30.0
        assert p.current_chapter == 4

    def test_update_complete(self):
        p = JobProgress()
        p.update(10, 10)
        assert p.percent_complete == 100.0
        assert p.current_chapter is None  # no next chapter

    def test_update_zero_total(self):
        p = JobProgress()
        p.update(0, 0)
        assert p.percent_complete == 0.0


# ---------------------------------------------------------------------------
# Unit tests: Job.to_dict
# ---------------------------------------------------------------------------

class TestJobToDict:
    def test_to_dict_structure(self):
        job = Job(job_id="test-123")
        d = job.to_dict()
        assert d["job_id"] == "test-123"
        assert d["status"] == "queued"
        assert "progress" in d
        assert d["progress"]["chapters_completed"] == 0
        assert d["is_partial"] is False
        assert d["result"] is None
        assert d["error"] is None

    def test_to_dict_with_result(self):
        job = Job(job_id="test-456")
        job.status = JobStatus.COMPLETED
        job.result = {"chapters": []}
        d = job.to_dict()
        assert d["status"] == "completed"
        assert d["result"] == {"chapters": []}


# ---------------------------------------------------------------------------
# Integration tests: BookJobQueue
# ---------------------------------------------------------------------------

class TestBookJobQueue:
    def test_submit_returns_job_id(self):
        queue = BookJobQueue()
        job_id = queue.submit(_fast_task, chapter_count=2)
        assert isinstance(job_id, str)
        assert len(job_id) > 0

    def test_job_initially_queued_or_processing(self):
        queue = BookJobQueue()
        job_id = queue.submit(_fast_task, chapter_count=2)
        # The job may already be processing by the time we check
        status = queue.get_job_status(job_id)
        assert status is not None
        assert status["status"] in ("queued", "processing", "completed")

    def test_job_completes_successfully(self):
        queue = BookJobQueue()
        job_id = queue.submit(_fast_task, chapter_count=2)

        # Wait for completion (up to 5 seconds)
        deadline = time.time() + 5
        while time.time() < deadline:
            status = queue.get_job_status(job_id)
            if status["status"] == "completed":
                break
            time.sleep(0.05)

        status = queue.get_job_status(job_id)
        assert status["status"] == "completed"
        assert status["result"] is not None
        assert status["is_partial"] is False

    def test_job_tracks_progress(self):
        queue = BookJobQueue()
        job_id = queue.submit(_fast_task, chapter_count=3)

        # Wait for completion
        deadline = time.time() + 5
        while time.time() < deadline:
            status = queue.get_job_status(job_id)
            if status["status"] == "completed":
                break
            time.sleep(0.05)

        status = queue.get_job_status(job_id)
        assert status["progress"]["chapters_completed"] == 3
        assert status["progress"]["total_chapters"] == 3
        assert status["progress"]["percent_complete"] == 100.0

    def test_job_fails_on_exception(self):
        queue = BookJobQueue()
        job_id = queue.submit(_failing_task, chapter_count=3)

        deadline = time.time() + 5
        while time.time() < deadline:
            status = queue.get_job_status(job_id)
            if status["status"] == "failed":
                break
            time.sleep(0.05)

        status = queue.get_job_status(job_id)
        assert status["status"] == "failed"
        assert status["error"] is not None
        assert "Simulated generation failure" in status["error"]

    def test_get_job_returns_none_for_unknown_id(self):
        queue = BookJobQueue()
        result = queue.get_job_status("nonexistent-id")
        assert result is None

    def test_list_jobs(self):
        queue = BookJobQueue()
        job_id1 = queue.submit(_fast_task, chapter_count=1)
        job_id2 = queue.submit(_fast_task, chapter_count=1)

        jobs = queue.list_jobs()
        job_ids = [j["job_id"] for j in jobs]
        assert job_id1 in job_ids
        assert job_id2 in job_ids

    def test_multiple_jobs_independent(self):
        """Multiple jobs should not interfere with each other."""
        queue = BookJobQueue()
        ids = [queue.submit(_fast_task, chapter_count=2) for _ in range(3)]

        deadline = time.time() + 10
        while time.time() < deadline:
            statuses = [queue.get_job_status(jid)["status"] for jid in ids]
            if all(s == "completed" for s in statuses):
                break
            time.sleep(0.05)

        for jid in ids:
            s = queue.get_job_status(jid)
            assert s["status"] == "completed"


# ---------------------------------------------------------------------------
# Timeout tests
# ---------------------------------------------------------------------------

class TestJobQueueTimeout:
    def test_timeout_constant_is_60_seconds(self):
        assert BOOK_GENERATION_TIMEOUT_SECONDS == 60

    def test_timeout_returns_partial_result(self):
        """
        When a job exceeds the timeout, it should return a partial result
        with whatever chapters were generated before the timeout.
        """
        # Use a very short timeout for testing by patching the constant
        queue = BookJobQueue()

        # Patch the timeout to 1 second so the test runs quickly
        with patch("backend.core.job_queue.BOOK_GENERATION_TIMEOUT_SECONDS", 1):
            # Re-create queue to pick up patched constant
            queue2 = BookJobQueue()
            job_id = queue2.submit(_partial_task, chapter_count=5)

            # Wait for timeout (up to 5 seconds)
            deadline = time.time() + 5
            while time.time() < deadline:
                status = queue2.get_job_status(job_id)
                if status["status"] in ("timeout", "completed", "failed"):
                    break
                time.sleep(0.1)

            status = queue2.get_job_status(job_id)
            assert status["status"] == "timeout"
            assert status["is_partial"] is True
            # Should have partial chapters
            assert status["result"] is not None
            assert "chapters" in status["result"]

    def test_timeout_job_has_partial_flag(self):
        """Timed-out jobs must set is_partial=True."""
        with patch("backend.core.job_queue.BOOK_GENERATION_TIMEOUT_SECONDS", 1):
            queue = BookJobQueue()
            job_id = queue.submit(_slow_task, chapter_count=10)

            deadline = time.time() + 5
            while time.time() < deadline:
                status = queue.get_job_status(job_id)
                if status["status"] in ("timeout", "completed", "failed"):
                    break
                time.sleep(0.1)

            status = queue.get_job_status(job_id)
            assert status["status"] == "timeout"
            assert status["is_partial"] is True


# ---------------------------------------------------------------------------
# Singleton tests
# ---------------------------------------------------------------------------

class TestGetJobQueue:
    def test_singleton_returns_same_instance(self):
        q1 = get_job_queue()
        q2 = get_job_queue()
        assert q1 is q2

    def test_singleton_is_book_job_queue(self):
        q = get_job_queue()
        assert isinstance(q, BookJobQueue)


# ---------------------------------------------------------------------------
# StoryEngine integration: BOOK mode returns job_id
# ---------------------------------------------------------------------------

class TestStoryEngineBookMode:
    """Verify that StoryEngine.generate_story for BOOK mode submits to the queue."""

    def test_book_mode_returns_job_id(self):
        """generate_story with BOOK mode should return a job_id immediately."""
        try:
            from backend.core.story_engine import StoryEngine
            from backend.core.data_models import StoryMode
        except ImportError:
            from core.story_engine import StoryEngine
            from core.data_models import StoryMode

        # Use a mock job queue to avoid actually running generation
        mock_queue = MagicMock(spec=BookJobQueue)
        mock_queue.submit.return_value = "mock-job-id-123"

        engine = StoryEngine(job_queue=mock_queue)

        # Run generate_story synchronously
        result = asyncio.run(
            engine.generate_story(
                location_name="Mumbai",
                year=1950,
                story_mode=StoryMode.BOOK,
                chapter_count=10,
            )
        )

        assert result["story_mode"] == "book"
        assert result["job_id"] == "mock-job-id-123"
        assert result["status"] == "queued"
        assert "mock-job-id-123" in result["message"]
        mock_queue.submit.assert_called_once()

    def test_book_mode_submit_passes_chapter_count(self):
        """The chapter_count should be forwarded to the job queue."""
        try:
            from backend.core.story_engine import StoryEngine
            from backend.core.data_models import StoryMode
        except ImportError:
            from core.story_engine import StoryEngine
            from core.data_models import StoryMode

        mock_queue = MagicMock(spec=BookJobQueue)
        mock_queue.submit.return_value = "job-abc"

        engine = StoryEngine(job_queue=mock_queue)

        asyncio.run(
            engine.generate_story(
                location_name="Delhi",
                year=1980,
                story_mode=StoryMode.BOOK,
                chapter_count=15,
            )
        )

        call_args = mock_queue.submit.call_args
        # Second positional arg to submit() is chapter_count
        assert call_args[0][1] == 15

"""
SCRIPTY - Background Job Queue for BOOK Generation
Implements async job processing for BOOK mode story generation.

Provides:
- Job queue system for async BOOK generation
- Job status tracking (queued, processing, completed, failed)
- Progress tracking (chapters_completed, percent_complete)
- 60-second timeout with partial book return

Requirements: 7.3, 16.4
"""
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

try:
    from backend.utils.logging_config import get_logger
except ImportError:
    from utils.logging_config import get_logger

logger = get_logger(__name__)

# Timeout for BOOK generation jobs (seconds)
BOOK_GENERATION_TIMEOUT_SECONDS = 60


class JobStatus(Enum):
    """Status of a background generation job."""
    QUEUED = "queued"           # Job is waiting to be processed
    PROCESSING = "processing"   # Job is currently being processed
    COMPLETED = "completed"     # Job finished successfully
    FAILED = "failed"           # Job failed with an error
    TIMEOUT = "timeout"         # Job exceeded the time limit (partial result available)


@dataclass
class JobProgress:
    """Progress information for a running job."""
    chapters_completed: int = 0
    total_chapters: int = 0
    percent_complete: float = 0.0
    current_chapter: Optional[int] = None

    def update(self, chapters_completed: int, total_chapters: int) -> None:
        """Update progress counters."""
        self.chapters_completed = chapters_completed
        self.total_chapters = total_chapters
        self.percent_complete = (
            round((chapters_completed / total_chapters) * 100, 1)
            if total_chapters > 0
            else 0.0
        )
        self.current_chapter = chapters_completed + 1 if chapters_completed < total_chapters else None


@dataclass
class Job:
    """Represents a single background generation job."""
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    progress: JobProgress = field(default_factory=JobProgress)
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    # Partial result when timeout occurs
    partial_result: Optional[dict] = None
    is_partial: bool = False

    def to_dict(self) -> dict:
        """Serialise job state to a plain dictionary for API responses."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": {
                "chapters_completed": self.progress.chapters_completed,
                "total_chapters": self.progress.total_chapters,
                "percent_complete": self.progress.percent_complete,
                "current_chapter": self.progress.current_chapter,
            },
            "result": self.result,
            "error": self.error,
            "is_partial": self.is_partial,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class BookJobQueue:
    """
    Thread-safe job queue for asynchronous BOOK generation.

    Each submitted job runs in a dedicated daemon thread. The queue stores
    job state so callers can poll for status and retrieve results.

    Requirements: 7.3, 16.4
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(
        self,
        task_fn: Callable[..., dict],
        chapter_count: int,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """
        Submit a BOOK generation task for background processing.

        The task function is called as ``task_fn(*args, **kwargs)`` inside a
        worker thread.  Progress updates are injected via a ``progress_callback``
        keyword argument that the task function should call after each chapter.

        Args:
            task_fn: Async-compatible callable that generates the book.
                     Must accept a ``progress_callback`` keyword argument.
            chapter_count: Total number of chapters (used for progress tracking).
            *args: Positional arguments forwarded to *task_fn*.
            **kwargs: Keyword arguments forwarded to *task_fn*.

        Returns:
            A unique job_id string that callers can use to poll status.
        """
        job_id = str(uuid.uuid4())
        job = Job(job_id=job_id)
        job.progress.total_chapters = chapter_count

        with self._lock:
            self._jobs[job_id] = job

        logger.info(
            "Job submitted",
            extra={"job_id": job_id, "chapter_count": chapter_count},
        )

        # Start worker thread
        thread = threading.Thread(
            target=self._run_job,
            args=(job_id, task_fn, chapter_count, args, kwargs),
            daemon=True,
            name=f"book-job-{job_id[:8]}",
        )
        thread.start()

        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Return the Job object for *job_id*, or None if not found."""
        with self._lock:
            return self._jobs.get(job_id)

    def get_job_status(self, job_id: str) -> Optional[dict]:
        """
        Return a serialised status dict for *job_id*, or None if not found.

        This is the primary method for API polling endpoints.
        """
        job = self.get_job(job_id)
        if job is None:
            return None
        return job.to_dict()

    def list_jobs(self) -> list[dict]:
        """Return serialised status for all tracked jobs."""
        with self._lock:
            return [job.to_dict() for job in self._jobs.values()]

    # ------------------------------------------------------------------
    # Internal worker
    # ------------------------------------------------------------------

    def _run_job(
        self,
        job_id: str,
        task_fn: Callable,
        chapter_count: int,
        args: tuple,
        kwargs: dict,
    ) -> None:
        """
        Execute the generation task in a background thread.

        Enforces a 60-second timeout.  If the timeout is exceeded, the partial
        result (chapters generated so far) is stored and the job is marked as
        TIMEOUT.

        Args:
            job_id: Identifier of the job being run.
            task_fn: The generation callable.
            chapter_count: Total chapters expected.
            args: Positional args for *task_fn*.
            kwargs: Keyword args for *task_fn*.
        """
        job = self._get_job_unsafe(job_id)
        if job is None:
            return

        # Mark as processing
        with self._lock:
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now(timezone.utc)

        logger.info("Job started", extra={"job_id": job_id})

        # Container for partial results collected via progress callback
        partial_chapters: list = []
        partial_result_holder: dict = {}

        def progress_callback(
            chapters_completed: int,
            chapter_data: Optional[Any] = None,
            partial_book_state: Optional[dict] = None,
        ) -> None:
            """
            Called by the task function after each chapter is generated.

            Args:
                chapters_completed: Number of chapters finished so far.
                chapter_data: The Chapter object just generated (optional).
                partial_book_state: Current partial book dict (optional).
            """
            with self._lock:
                job.progress.update(chapters_completed, chapter_count)
                if chapter_data is not None:
                    partial_chapters.append(chapter_data)
                if partial_book_state is not None:
                    partial_result_holder.update(partial_book_state)

            logger.debug(
                "Job progress",
                extra={
                    "job_id": job_id,
                    "chapters_completed": chapters_completed,
                    "percent_complete": job.progress.percent_complete,
                },
            )

        # Inject the callback into kwargs
        kwargs["progress_callback"] = progress_callback

        # Run the task in a sub-thread so we can enforce a timeout
        result_holder: dict = {}
        error_holder: dict = {}

        def _task_wrapper() -> None:
            import asyncio
            try:
                # task_fn is a coroutine function – run it in a new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(task_fn(*args, **kwargs))
                    result_holder["result"] = result
                finally:
                    loop.close()
            except Exception as exc:  # noqa: BLE001
                error_holder["error"] = str(exc)
                logger.exception(
                    "Job task raised an exception",
                    extra={"job_id": job_id},
                )

        task_thread = threading.Thread(
            target=_task_wrapper,
            daemon=True,
            name=f"book-task-{job_id[:8]}",
        )
        task_thread.start()
        task_thread.join(timeout=BOOK_GENERATION_TIMEOUT_SECONDS)

        with self._lock:
            job.completed_at = datetime.now(timezone.utc)

            if task_thread.is_alive():
                # Timeout: return whatever chapters were generated
                logger.warning(
                    "Job timed out after %ds, returning partial result",
                    BOOK_GENERATION_TIMEOUT_SECONDS,
                    extra={"job_id": job_id},
                )
                job.status = JobStatus.TIMEOUT
                job.is_partial = True

                # Build a partial result from collected chapters
                partial = dict(partial_result_holder)
                partial["chapters"] = partial_chapters
                partial["is_partial"] = True
                partial["chapters_completed"] = job.progress.chapters_completed
                partial["total_chapters_requested"] = chapter_count
                job.result = partial

            elif "error" in error_holder:
                job.status = JobStatus.FAILED
                job.error = error_holder["error"]
                logger.error(
                    "Job failed",
                    extra={"job_id": job_id, "error": job.error},
                )

            else:
                job.status = JobStatus.COMPLETED
                job.result = result_holder.get("result")
                logger.info(
                    "Job completed successfully",
                    extra={"job_id": job_id},
                )

        logger.info(
            "Job finished",
            extra={
                "job_id": job_id,
                "status": job.status.value,
                "is_partial": job.is_partial,
            },
        )

    def _get_job_unsafe(self, job_id: str) -> Optional[Job]:
        """Return job without acquiring the lock (caller must hold it or be safe)."""
        return self._jobs.get(job_id)


# ---------------------------------------------------------------------------
# Module-level singleton – shared across the application
# ---------------------------------------------------------------------------
_default_queue: Optional[BookJobQueue] = None
_queue_lock = threading.Lock()


def get_job_queue() -> BookJobQueue:
    """Return the application-wide BookJobQueue singleton."""
    global _default_queue
    if _default_queue is None:
        with _queue_lock:
            if _default_queue is None:
                _default_queue = BookJobQueue()
    return _default_queue

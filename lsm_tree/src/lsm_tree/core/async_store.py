"""Async LSM Store implementation with non-blocking compaction.

Extends SimpleLSMStore to run compactions in the background without blocking writes.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import LSMConfig

from .store import SimpleLSMStore

logger = logging.getLogger(__name__)


class CompactionStatus(Enum):
    """Status of a compaction job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CompactionJob:
    """Represents a compaction job."""

    job_id: int
    level: int
    status: CompactionStatus
    error: Exception | None = None
    started_at: float | None = None
    completed_at: float | None = None


class AsyncLSMStore(SimpleLSMStore):
    """LSM Store with asynchronous background compaction.

    Extends SimpleLSMStore to add:
    - Background compaction worker thread
    - Non-blocking compaction scheduling
    - Job tracking and status queries
    - Optional wait-for-completion

    Args:
        config: LSM configuration
        max_concurrent_compactions: Max number of concurrent compaction jobs per level

    Public API (in addition to SimpleLSMStore):
        - schedule_compaction(level, wait=False): Schedule background compaction
        - wait_for_compaction(job_id, timeout=None): Wait for specific job
        - get_compaction_status(job_id): Query job status
        - list_pending_compactions(): List all pending jobs
    """

    def __init__(self, config: LSMConfig, max_concurrent_compactions: int = 1):
        """Initialize async LSM store with background compaction."""
        super().__init__(config)

        # Compaction job management
        self._compaction_queue: queue.Queue[CompactionJob | None] = queue.Queue()
        self._active_jobs: dict[int, CompactionJob] = {}
        self._completed_jobs: dict[int, CompactionJob] = {}
        self._job_counter: int = 0
        self._jobs_lock: threading.Lock = threading.Lock()

        # Per-level compaction gating (only one job per level at a time)
        self._level_locks: dict[int, threading.Lock] = {
            i: threading.Lock() for i in range(config.max_levels)
        }

        # Compaction worker thread
        self._shutdown: bool = False
        self._worker_thread: threading.Thread = threading.Thread(
            target=self._compaction_worker, daemon=True, name="CompactionWorker"
        )
        self._worker_thread.start()

        logger.info("Initialized AsyncLSMStore with background compaction")

    def schedule_compaction(self, level: int, wait: bool = False) -> int:
        """Schedule a compaction job for a level.

        Args:
            level: Level to compact (0 to max_levels-2)
            wait: If True, block until compaction completes

        Returns:
            Job ID for tracking

        Raises:
            ValueError: If level is invalid
        """
        if level >= self.config.max_levels - 1:
            raise ValueError(f"Cannot compact level {level}, at max level")  # noqa: TRY003

        with self._jobs_lock:
            self._job_counter += 1
            job = CompactionJob(
                job_id=self._job_counter, level=level, status=CompactionStatus.PENDING
            )
            self._active_jobs[job.job_id] = job

        logger.info(f"Scheduled compaction job {job.job_id} for level {level}")
        self._compaction_queue.put(job)

        if wait:
            self.wait_for_compaction(job.job_id)

        return job.job_id

    def wait_for_compaction(self, job_id: int, timeout: float | None = None) -> bool:
        """Wait for a compaction job to complete.

        Args:
            job_id: Job ID to wait for
            timeout: Maximum time to wait in seconds (None = infinite)

        Returns:
            True if job completed successfully, False if timeout or failed
        """
        deadline = time.time() + timeout if timeout else None

        while True:
            with self._jobs_lock:
                if job_id in self._completed_jobs:
                    job = self._completed_jobs[job_id]
                    return job.status == CompactionStatus.COMPLETED

                if job_id not in self._active_jobs:
                    logger.warning(f"Job {job_id} not found")
                    return False

            if deadline and time.time() >= deadline:
                logger.warning(f"Timeout waiting for job {job_id}")
                return False

            time.sleep(0.01)  # 10ms poll interval

    def get_compaction_status(self, job_id: int) -> CompactionJob | None:
        """Get status of a compaction job.

        Args:
            job_id: Job ID to query

        Returns:
            CompactionJob if found, None otherwise
        """
        with self._jobs_lock:
            if job_id in self._active_jobs:
                return self._active_jobs[job_id]
            if job_id in self._completed_jobs:
                return self._completed_jobs[job_id]
        return None

    def list_pending_compactions(self) -> list[CompactionJob]:
        """List all pending and running compaction jobs.

        Returns:
            List of active CompactionJob objects
        """
        with self._jobs_lock:
            return list(self._active_jobs.values())

    def _compaction_worker(self) -> None:
        """Background thread that processes compaction jobs."""
        logger.info("Compaction worker started")

        while not self._shutdown:
            try:
                # Get next job (blocks until available or timeout)
                try:
                    job = self._compaction_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                if job is None:  # Shutdown signal
                    break

                self._process_compaction_job(job)

            except Exception:
                logger.exception("Error in compaction worker")

        logger.info("Compaction worker stopped")

    def _process_compaction_job(self, job: CompactionJob) -> None:
        """Process a single compaction job.

        Args:
            job: CompactionJob to process
        """
        level = job.level

        # Try to acquire level lock (non-blocking)
        if not self._level_locks[level].acquire(blocking=False):
            logger.info(
                f"Level {level} already compacting, requeueing job {job.job_id}"
            )
            # Requeue with small delay
            time.sleep(0.1)
            self._compaction_queue.put(job)
            return

        try:
            # Update job status
            with self._jobs_lock:
                job.status = CompactionStatus.RUNNING
                job.started_at = time.time()

            logger.info(f"Starting compaction job {job.job_id} for level {level}")

            # Perform compaction outside the main lock
            # This is the key to non-blocking: we only hold _lock briefly for catalog updates
            input_tables = self._catalog.list_level(level)

            if not input_tables:
                logger.info(f"No SSTables at level {level}, skipping job {job.job_id}")
                with self._jobs_lock:
                    job.status = CompactionStatus.COMPLETED
                    job.completed_at = time.time()
                    self._completed_jobs[job.job_id] = job
                    del self._active_jobs[job.job_id]
                return

            # Run compaction (I/O intensive, done outside main lock)
            output_metas = self._compactor.compact(input_tables, level + 1)

            # Brief critical section: update catalog atomically
            with self._lock:
                self._catalog.remove_sstables(input_tables)
                for meta in output_metas:
                    self._catalog.add_sstable(level + 1, meta)

            # Delete old files (outside lock)
            for meta in input_tables:
                try:
                    Path(meta["data_path"]).unlink()
                    Path(meta["meta_path"]).unlink()
                except Exception as e:  # noqa: PERF203
                    logger.warning(f"Failed to delete old SSTable: {e}")

            # Mark job as completed
            with self._jobs_lock:
                job.status = CompactionStatus.COMPLETED
                job.completed_at = time.time()
                self._completed_jobs[job.job_id] = job
                del self._active_jobs[job.job_id]

            logger.info(
                f"Completed compaction job {job.job_id} for level {level} "
                f"in {job.completed_at - job.started_at:.2f}s"
            )

        except Exception as e:
            logger.exception(f"Compaction job {job.job_id} failed")
            with self._jobs_lock:
                job.status = CompactionStatus.FAILED
                job.error = e
                job.completed_at = time.time()
                self._completed_jobs[job.job_id] = job
                del self._active_jobs[job.job_id]

        finally:
            self._level_locks[level].release()

    def close(self) -> None:
        """Close store and shutdown background workers."""
        logger.info("Shutting down AsyncLSMStore")

        # Signal shutdown
        self._shutdown = True
        self._compaction_queue.put(None)

        # Wait for worker to finish
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
            if self._worker_thread.is_alive():
                logger.warning("Compaction worker did not shut down cleanly")

        # Close parent
        super().close()

    def compact_level(self, level: int) -> None:
        """Trigger synchronous compaction (for compatibility).

        This method schedules a compaction and waits for it to complete.
        For async operation, use schedule_compaction() instead.

        Args:
            level: Level to compact
        """
        job_id = self.schedule_compaction(level, wait=False)
        self.wait_for_compaction(job_id)

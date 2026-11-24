"""In-memory job tracker for admin-triggered background jobs."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobRecord:
    job_id: str
    job_type: str
    status: JobStatus
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "details": self.details,
        }


class JobTracker:
    """Thread-safe in-memory tracker for background jobs.

    Keeps at most ``max_history`` completed records. Only one job per
    ``job_type`` can be running at a time.
    """

    def __init__(self, max_history: int = 50):
        self._lock = threading.Lock()
        self._jobs: dict[str, JobRecord] = {}
        self._max_history = max_history

    def start(self, job_type: str, details: dict | None = None) -> JobRecord:
        """Register a new running job. Raises ValueError if already running."""
        with self._lock:
            for rec in self._jobs.values():
                if rec.job_type == job_type and rec.status in (
                    JobStatus.STARTED,
                    JobStatus.RUNNING,
                ):
                    raise ValueError(f"Job type '{job_type}' is already running")

            job_id = uuid.uuid4().hex[:12]
            record = JobRecord(
                job_id=job_id,
                job_type=job_type,
                status=JobStatus.STARTED,
                started_at=datetime.now(),
                details=details or {},
            )
            self._jobs[job_id] = record
            self._prune_old()
            return record

    def mark_running(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].status = JobStatus.RUNNING

    def mark_completed(self, job_id: str, details: dict | None = None) -> None:
        with self._lock:
            if job_id in self._jobs:
                rec = self._jobs[job_id]
                rec.status = JobStatus.COMPLETED
                rec.completed_at = datetime.now()
                if details:
                    rec.details.update(details)

    def mark_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                rec = self._jobs[job_id]
                rec.status = JobStatus.FAILED
                rec.completed_at = datetime.now()
                rec.error = error

    def is_running(self, job_type: str) -> bool:
        with self._lock:
            return any(
                r.job_type == job_type and r.status in (JobStatus.STARTED, JobStatus.RUNNING)
                for r in self._jobs.values()
            )

    def list_jobs(self, limit: int = 20) -> list[dict]:
        with self._lock:
            records = sorted(self._jobs.values(), key=lambda r: r.started_at, reverse=True)
            return [r.to_dict() for r in records[:limit]]

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _prune_old(self) -> None:
        """Remove oldest completed jobs when exceeding max_history."""
        completed = [
            (jid, rec)
            for jid, rec in self._jobs.items()
            if rec.status in (JobStatus.COMPLETED, JobStatus.FAILED)
        ]
        if len(completed) > self._max_history:
            completed.sort(key=lambda x: x[1].started_at)
            for jid, _ in completed[: len(completed) - self._max_history]:
                del self._jobs[jid]


# Singleton instance used by the admin router
job_tracker = JobTracker()

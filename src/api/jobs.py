from __future__ import annotations

import uuid
from datetime import datetime


class JobTracker:
    """In-memory job status tracker. Jobs are lost on server restart."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}

    def start(self, job_type: str, params: dict | None = None) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "job_id": job_id,
            "job_type": job_type,
            "status": "started",
            "message": f"{job_type} job started",
            "params": params or {},
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "error": None,
        }
        return job_id

    def complete(self, job_id: str, summary: str = "") -> None:
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = "completed"
            self._jobs[job_id]["message"] = summary or "Job completed successfully"
            self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

    def fail(self, job_id: str, error: str) -> None:
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = "failed"
            self._jobs[job_id]["message"] = f"Job failed: {error}"
            self._jobs[job_id]["error"] = error
            self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

    def get_status(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)


# Singleton instance
job_tracker = JobTracker()

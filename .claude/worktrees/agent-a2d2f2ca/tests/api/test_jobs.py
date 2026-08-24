from __future__ import annotations

from src.api.jobs import JobTracker


class TestJobTrackerStart:
    def test_generates_unique_ids(self) -> None:
        tracker = JobTracker()
        id1 = tracker.start("backfill")
        id2 = tracker.start("backfill")
        assert id1 != id2

    def test_sets_status_to_started(self) -> None:
        tracker = JobTracker()
        job_id = tracker.start("backfill", {"set": "dmr"})
        status = tracker.get_status(job_id)
        assert status is not None
        assert status["status"] == "started"
        assert status["job_type"] == "backfill"
        assert status["params"] == {"set": "dmr"}
        assert status["message"] == "backfill job started"
        assert status["started_at"] is not None
        assert status["completed_at"] is None
        assert status["error"] is None

    def test_default_params_empty_dict(self) -> None:
        tracker = JobTracker()
        job_id = tracker.start("update")
        status = tracker.get_status(job_id)
        assert status is not None
        assert status["params"] == {}


class TestJobTrackerComplete:
    def test_updates_status_to_completed(self) -> None:
        tracker = JobTracker()
        job_id = tracker.start("backfill")
        tracker.complete(job_id, "Processed 10 cards")
        status = tracker.get_status(job_id)
        assert status is not None
        assert status["status"] == "completed"
        assert status["message"] == "Processed 10 cards"
        assert status["completed_at"] is not None

    def test_default_summary_message(self) -> None:
        tracker = JobTracker()
        job_id = tracker.start("backfill")
        tracker.complete(job_id)
        status = tracker.get_status(job_id)
        assert status is not None
        assert status["message"] == "Job completed successfully"

    def test_complete_unknown_id_is_noop(self) -> None:
        tracker = JobTracker()
        tracker.complete("nonexistent")  # should not raise


class TestJobTrackerFail:
    def test_updates_status_to_failed(self) -> None:
        tracker = JobTracker()
        job_id = tracker.start("backfill")
        tracker.fail(job_id, "Connection timeout")
        status = tracker.get_status(job_id)
        assert status is not None
        assert status["status"] == "failed"
        assert status["message"] == "Job failed: Connection timeout"
        assert status["error"] == "Connection timeout"
        assert status["completed_at"] is not None

    def test_fail_unknown_id_is_noop(self) -> None:
        tracker = JobTracker()
        tracker.fail("nonexistent", "error")  # should not raise


class TestJobTrackerGetStatus:
    def test_returns_none_for_unknown_id(self) -> None:
        tracker = JobTracker()
        assert tracker.get_status("does-not-exist") is None

    def test_multiple_jobs_tracked_independently(self) -> None:
        tracker = JobTracker()
        id1 = tracker.start("backfill", {"set": "dmr"})
        id2 = tracker.start("update")

        tracker.complete(id1, "Done backfill")
        tracker.fail(id2, "Network error")

        s1 = tracker.get_status(id1)
        s2 = tracker.get_status(id2)
        assert s1 is not None
        assert s2 is not None
        assert s1["status"] == "completed"
        assert s2["status"] == "failed"

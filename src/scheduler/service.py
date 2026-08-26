"""Scan scheduler service -- manages APScheduler lifecycle for automated price scans.

Uses BackgroundScheduler (threading-based) with in-memory job store.
Each scheduled scan maps to an APScheduler CronTrigger job.
Schedule metadata (last_run, error_count, next_run) lives in the
scheduled_scans DB table.
"""

from __future__ import annotations

import asyncio
import re
import threading
from datetime import datetime

import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter

from src.database.repository import Repository
from src.domain.models import ScanFilter

log = structlog.get_logger()


def validate_cron(expression: str) -> None:
    """Validate a cron expression. Raises ValueError if invalid or sub-hour."""
    if not croniter.is_valid(expression):
        raise ValueError(f"Invalid cron expression: {expression}")

    # Reject sub-hour intervals
    parts = expression.strip().split()
    if len(parts) >= 1:
        minute_field = parts[0]
        # Reject */N where N < 60 (e.g. */5, */15, */30)
        match = re.match(r"^\*/(\d+)$", minute_field)
        if match:
            interval = int(match.group(1))
            if interval < 60:
                raise ValueError(
                    f"Sub-hour cron intervals are not allowed (minimum 1 hour). Got: {expression}"
                )
        # Reject bare * in minute field (runs every minute)
        if minute_field == "*":
            raise ValueError(
                f"Sub-hour cron intervals are not allowed (minimum 1 hour). Got: {expression}"
            )


class ScanScheduler:
    """Manages APScheduler lifecycle for automated price scans.

    Uses BackgroundScheduler (threading-based). Each schedule maps to an
    APScheduler CronTrigger job. Job persistence is handled by the
    scheduled_scans table, not APScheduler's internal job store.
    """

    def __init__(self, db_url: str):
        self._db_url = db_url
        self._scheduler: BackgroundScheduler | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        """Initialize APScheduler, load active schedules from DB, start."""
        self._scheduler = BackgroundScheduler()
        self._scheduler.start()

        repo = Repository(self._db_url)
        active = repo.get_active_schedules()
        for schedule in active:
            try:
                self._add_job(schedule)
                log.info(
                    "schedule_loaded",
                    schedule_id=schedule["id"],
                    name=schedule["name"],
                    cron=schedule["cron_expression"],
                )
            except Exception as e:
                log.warning(
                    "schedule_load_failed",
                    schedule_id=schedule["id"],
                    error=str(e),
                )

        log.info("scheduler_started", active_schedules=len(active))

    def shutdown(self) -> None:
        """Gracefully stop the scheduler."""
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
            log.info("scheduler_stopped")

    def add_schedule(self, schedule_id: int) -> None:
        """Read schedule from DB, create APScheduler job with CronTrigger."""
        repo = Repository(self._db_url)
        schedule = repo.get_scheduled_scan(schedule_id)
        if schedule is None:
            raise ValueError(f"Schedule {schedule_id} not found")
        self._add_job(schedule)

    def remove_schedule(self, schedule_id: int) -> None:
        """Remove APScheduler job for given schedule."""
        if self._scheduler is None:
            return
        job_id = self._job_id(schedule_id)
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            log.info("schedule_removed", schedule_id=schedule_id)

    def pause_schedule(self, schedule_id: int) -> None:
        """Pause an APScheduler job."""
        if self._scheduler is None:
            return
        job_id = self._job_id(schedule_id)
        if self._scheduler.get_job(job_id):
            self._scheduler.pause_job(job_id)
            log.info("schedule_paused", schedule_id=schedule_id)

    def resume_schedule(self, schedule_id: int) -> None:
        """Resume a paused APScheduler job."""
        if self._scheduler is None:
            return
        job_id = self._job_id(schedule_id)
        if self._scheduler.get_job(job_id):
            self._scheduler.resume_job(job_id)
            log.info("schedule_resumed", schedule_id=schedule_id)

    def trigger_now(self, schedule_id: int) -> int:
        """Manually trigger a schedule immediately. Returns scan_run ID."""
        repo = Repository(self._db_url)
        schedule = repo.get_scheduled_scan(schedule_id)
        if schedule is None:
            raise ValueError(f"Schedule {schedule_id} not found")

        # Create scan run
        scan_id = repo.create_scan_run(schedule["scan_type"], schedule["filters_json"])

        # Launch in background thread
        thread = threading.Thread(
            target=self._execute_scheduled_scan,
            args=(schedule_id, scan_id),
            daemon=True,
        )
        thread.start()

        return scan_id

    def _execute_scheduled_scan(self, schedule_id: int, scan_id: int | None = None) -> None:
        """Callback executed by APScheduler. Runs scan, updates schedule metadata.

        Routes to Liga provider when filters_json contains ``"provider": "liga"``.
        """
        with self._lock:
            repo = Repository(self._db_url)
            schedule = repo.get_scheduled_scan(schedule_id)
            if schedule is None:
                log.warning("schedule_not_found", schedule_id=schedule_id)
                return

            # Concurrency guard: skip if previous scan still running
            if schedule["last_run_id"] is not None:
                last_run = repo.get_scan_run(schedule["last_run_id"])
                if last_run and last_run["status"] in ("pending", "running"):
                    log.warning(
                        "schedule_skip_concurrent",
                        schedule_id=schedule_id,
                        last_run_id=schedule["last_run_id"],
                    )
                    return

            # Create scan run if not provided (APScheduler callback)
            if scan_id is None:
                scan_id = repo.create_scan_run(schedule["scan_type"], schedule["filters_json"])

        try:
            scan_filter = ScanFilter.from_json(schedule["filters_json"])

            # Determine provider from filters_json
            import json as _json

            try:
                filters_data = _json.loads(schedule["filters_json"] or "{}")
            except (ValueError, TypeError):
                filters_data = {}
            provider_name = filters_data.get("provider", "myp")

            if schedule["scan_type"] == "admin_daily_liga":
                from src.collectors.admin_scan import run_admin_daily_liga_scan
                from src.services.scan_hooks import default_registry

                max_age_days = filters_data.get("max_age_days", 1)
                asyncio.run(
                    run_admin_daily_liga_scan(
                        db_url=self._db_url,
                        run_id=scan_id,
                        max_age_days=max_age_days,
                        on_complete=default_registry.notify,
                    )
                )
            elif provider_name == "liga":
                from src.collectors.liga_scan import run_liga_scan

                max_age_days = filters_data.get("max_age_days")
                asyncio.run(
                    run_liga_scan(
                        db_url=self._db_url,
                        scan_filter=scan_filter,
                        run_id=scan_id,
                        max_age_days=max_age_days,
                    )
                )
            else:
                from src.collectors.scan import run_scan

                asyncio.run(
                    run_scan(
                        db_url=self._db_url,
                        scan_filter=scan_filter,
                        run_id=scan_id,
                    )
                )

            # Success: update schedule metadata
            repo = Repository(self._db_url)
            repo.update_scheduled_scan(
                schedule_id,
                last_run_id=scan_id,
                last_run_at=datetime.now(),
                error_count=0,
            )
            self._update_next_run(schedule_id)

            log.info(
                "scheduled_scan_completed",
                schedule_id=schedule_id,
                scan_id=scan_id,
            )

        except Exception as e:
            log.error(
                "scheduled_scan_failed",
                schedule_id=schedule_id,
                scan_id=scan_id,
                error=str(e),
            )

            # Increment error count, auto-pause if needed
            repo = Repository(self._db_url)
            schedule = repo.get_scheduled_scan(schedule_id)
            if schedule is None:
                return

            new_error_count = schedule["error_count"] + 1
            updates: dict = {
                "last_run_id": scan_id,
                "last_run_at": datetime.now(),
                "error_count": new_error_count,
            }

            if new_error_count >= schedule["max_retries"]:
                updates["status"] = "paused"
                self.pause_schedule(schedule_id)
                log.warning(
                    "schedule_auto_paused",
                    schedule_id=schedule_id,
                    error_count=new_error_count,
                    max_retries=schedule["max_retries"],
                )

            repo.update_scheduled_scan(schedule_id, **updates)

    def _add_job(self, schedule: dict) -> None:
        """Register an APScheduler CronTrigger job from a schedule dict."""
        if self._scheduler is None:
            raise RuntimeError("Scheduler not started")

        job_id = self._job_id(schedule["id"])

        # Remove existing job if present
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        trigger = CronTrigger.from_crontab(schedule["cron_expression"])
        self._scheduler.add_job(
            self._execute_scheduled_scan,
            trigger=trigger,
            id=job_id,
            args=[schedule["id"]],
            name=schedule["name"],
            replace_existing=True,
        )

    def _update_next_run(self, schedule_id: int) -> None:
        """Update next_run_at from the CronTrigger's next fire time."""
        if self._scheduler is None:
            return
        job_id = self._job_id(schedule_id)
        job = self._scheduler.get_job(job_id)
        if job and job.next_run_time:
            repo = Repository(self._db_url)
            repo.update_scheduled_scan(
                schedule_id, next_run_at=job.next_run_time.replace(tzinfo=None)
            )

    @staticmethod
    def _job_id(schedule_id: int) -> str:
        """Build APScheduler job ID from schedule ID."""
        return f"scheduled_scan_{schedule_id}"

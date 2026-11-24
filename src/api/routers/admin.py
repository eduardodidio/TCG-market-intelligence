"""Admin router -- user management, credit adjustments, platform stats,
job triggers, DB backup, and audit log (F100)."""

from __future__ import annotations

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.background import BackgroundTask

from src.api.deps import get_audit_service, get_db, require_admin
from src.api.error_codes import ErrorCode, api_error
from src.api.job_tracker import job_tracker
from src.api.schemas.admin import (
    CreateUserRequest,
    CreateUserResponse,
    CreditAdjustRequest,
    ResetPasswordResponse,
)
from src.api.schemas.envelope import success_response
from src.auth.passwords import hash_password
from src.credits.service import CreditService
from src.database.repository import Repository
from src.domain.models import User
from src.services.audit import AuditService

router = APIRouter(prefix="/admin", tags=["admin"])

_INITIAL_CREDITS = 50


# ── User management ─────────────────────────────────────────────────


@router.post("/users")
def create_user(
    body: CreateUserRequest,
    request: Request,
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
):
    """Create a new user with a temporary password (admin only).

    The temporary password is returned once and must be changed on first login.
    """
    existing = repo.get_user_by_email(body.email)
    if existing:
        raise api_error(409, ErrorCode.AUTH_EMAIL_TAKEN, "Email already registered")

    temp_password = secrets.token_urlsafe(12)
    pw_hash = hash_password(temp_password)

    user = repo.create_user(
        email=body.email,
        display_name=body.display_name,
        auth_provider="email",
        password_hash=pw_hash,
    )

    # Set password as immediately expired
    repo.update_user(user.id, password_expires_at=datetime.now())

    # Grant initial credits
    svc = CreditService(repo)
    svc.grant(user.id, _INITIAL_CREDITS, "initial_grant", reference_id=f"admin:{admin.id}")

    audit.log(
        actor=admin,
        action="user_create",
        target_type="user",
        target_id=str(user.id),
        details={"email": body.email, "display_name": body.display_name},
        ip_address=request.client.host if request.client else None,
    )

    return success_response(
        data=CreateUserResponse(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            temporary_password=temp_password,
        ).model_dump()
    )


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
):
    """Soft-delete a user (sets is_active=0). Admin only. Cannot delete self."""
    if user_id == admin.id:
        raise api_error(400, ErrorCode.AUTHZ_FORBIDDEN, "Cannot delete yourself")

    target = repo.get_user_by_id(user_id)
    if not target:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "User not found")

    repo.update_user(user_id, is_active=0)

    audit.log(
        actor=admin,
        action="user_delete",
        target_type="user",
        target_id=str(user_id),
        details={"email": target.email},
        ip_address=request.client.host if request.client else None,
    )

    return success_response(data={"user_id": user_id, "deleted": True})


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
):
    """Reset a user's password (admin only).

    Generates a new temporary password that expires immediately,
    forcing the user to change it on next login.
    """
    if user_id == admin.id:
        raise api_error(400, ErrorCode.AUTHZ_FORBIDDEN, "Cannot reset your own password via admin")

    target = repo.get_user_by_id(user_id)
    if not target:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "User not found")

    temp_password = secrets.token_urlsafe(12)
    pw_hash = hash_password(temp_password)

    repo.update_user(user_id, password_hash=pw_hash, password_expires_at=datetime.now())

    return success_response(
        data=ResetPasswordResponse(
            user_id=user_id,
            email=target.email,
            temporary_password=temp_password,
        ).model_dump()
    )


@router.get("/users")
def list_users(
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all users with credit balances (admin only)."""
    users, total = repo.list_users_with_balances(limit=limit, offset=offset)
    return success_response(data=users, total=total, offset=offset)


@router.patch("/users/{user_id}/credits")
def adjust_credits(
    user_id: int,
    body: CreditAdjustRequest,
    request: Request,
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
):
    """Grant or revoke credits for a user (admin only).

    Positive amount = grant. Negative amount = revoke.
    Revoke is clamped: balance cannot go below 0.
    """
    # Verify target user exists
    target = repo.get_user_by_id(user_id)
    if not target:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "User not found")

    svc = CreditService(repo)
    reason = body.reason or "admin_adjust"

    if body.amount >= 0:
        balance = svc.grant(user_id, body.amount, reason, reference_id=f"admin:{admin.id}")
        amount_applied = body.amount
    else:
        # For revocation, clamp to available balance
        current = svc.get_balance(user_id)
        actual_deduct = min(abs(body.amount), current.balance)
        if actual_deduct > 0:
            balance = svc.deduct(user_id, actual_deduct, reason, reference_id=f"admin:{admin.id}")
        else:
            balance = current
        amount_applied = -actual_deduct

    audit.log(
        actor=admin,
        action="credit_adjust",
        target_type="user",
        target_id=str(user_id),
        details={
            "amount_requested": body.amount,
            "amount_applied": amount_applied,
            "reason": reason,
            "new_balance": balance.balance,
        },
        ip_address=request.client.host if request.client else None,
    )

    return success_response(
        data={
            "user_id": user_id,
            "new_balance": balance.balance,
            "amount_applied": amount_applied,
        }
    )


# ── Platform stats ───────────────────────────────────────────────────


@router.get("/dashboard")
def admin_dashboard(
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
):
    """Platform stats (admin only)."""
    stats = repo.get_platform_stats()
    return success_response(data=stats)


# ── Error logs ───────────────────────────────────────────────────────


@router.get("/errors")
def list_errors(
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    level: str | None = Query(None),
    module: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List application errors with filters (admin only)."""
    errors, total = repo.list_error_logs(
        level=level,
        module=module,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return success_response(data=errors, total=total, offset=offset)


@router.get("/errors/{error_id}")
def get_error(
    error_id: str,
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
):
    """Get full error detail (admin only)."""
    import json as json_mod

    error = repo.get_error_log(error_id)
    if error is None:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Error not found")

    # Parse JSON string fields into dicts
    if isinstance(error.get("request_params"), str):
        try:
            error["request_params"] = json_mod.loads(error["request_params"])
        except (json_mod.JSONDecodeError, TypeError):
            error["request_params"] = None
    if isinstance(error.get("extra"), str):
        try:
            error["extra"] = json_mod.loads(error["extra"])
        except (json_mod.JSONDecodeError, TypeError):
            error["extra"] = None

    return success_response(data=error)


# ── Audit log (F100-T02) ────────────────────────────────────────────


@router.get("/audit-log")
def list_audit_log(
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    action: str | None = Query(None),
    actor_id: int | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List audit log entries with optional filters (admin only)."""
    logs, total = repo.list_audit_logs(
        limit=limit,
        offset=offset,
        action=action,
        actor_id=actor_id,
        date_from=date_from,
        date_to=date_to,
    )
    return success_response(data=logs, total=total, offset=offset)


# ── Job triggers (F100-T03) ─────────────────────────────────────────


@router.get("/jobs/status")
def get_job_status(
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
):
    """List recent admin-triggered job runs (scan_runs + in-memory tracker)."""
    scan_runs = repo.list_scan_runs(limit=limit, offset=0)
    tracked_jobs = job_tracker.list_jobs(limit=limit)
    return success_response(data={"scan_runs": scan_runs, "tracked_jobs": tracked_jobs})


# ── MYP sweep job (F213-T04) ────────────────────────────────────────


@router.post("/jobs/myp-sweep")
def trigger_myp_sweep(
    request: Request,
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    max_age_days: int = Query(1, ge=1, le=30),
    limit: int | None = Query(None, ge=1, le=5000),
):
    """Trigger a MYP Cards price sweep for collection cards (admin only).

    Runs in a background thread. Returns 409 if a sweep is already running.
    """
    import asyncio
    import threading

    from src.collectors.myp_sweep import run_myp_sweep
    from src.config import get_db_url

    if job_tracker.is_running("myp-sweep"):
        raise api_error(409, ErrorCode.RESOURCE_CONFLICT, "MYP sweep is already running")

    job = job_tracker.start("myp-sweep", {"max_age_days": max_age_days, "limit": limit})
    db_url = get_db_url()

    def _run():
        try:
            job_tracker.mark_running(job.job_id)
            result = asyncio.run(
                run_myp_sweep(
                    db_url=db_url,
                    max_age_days=max_age_days,
                    limit=limit,
                )
            )
            job_tracker.mark_completed(
                job.job_id,
                {"cards_processed": result.cards_processed if result else 0},
            )
        except Exception as exc:
            job_tracker.mark_failed(job.job_id, str(exc))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    audit.log(
        actor=admin,
        action="job_trigger",
        target_type="job",
        target_id=job.job_id,
        details={"job_type": "myp-sweep", "max_age_days": max_age_days, "limit": limit},
        ip_address=request.client.host if request.client else None,
    )

    return success_response(data={"job_id": job.job_id, "status": "started", "type": "myp-sweep"})


# ── Portfolio snapshot job (F213-T04) ────────────────────────────────


@router.post("/jobs/snapshot-portfolio")
def trigger_snapshot_portfolio(
    request: Request,
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
):
    """Snapshot portfolio values for all active users (admin only).

    Runs in a background thread. Returns 409 if already running.
    """
    import threading

    from src.config import get_db_url

    if job_tracker.is_running("snapshot-portfolio"):
        raise api_error(409, ErrorCode.RESOURCE_CONFLICT, "Portfolio snapshot is already running")

    job = job_tracker.start("snapshot-portfolio")
    db_url = get_db_url()

    def _run():
        from sqlalchemy import select
        from sqlalchemy.orm import Session as SaSession

        from src.collectors.portfolio_snapshot import take_snapshot
        from src.database.models import UserRow
        from src.database.repository import Repository as Repo

        try:
            job_tracker.mark_running(job.job_id)
            snap_repo = Repo(db_url=db_url)
            count = 0
            with SaSession(snap_repo.engine) as session:
                users = (
                    session.execute(select(UserRow).where(UserRow.is_active == 1)).scalars().all()
                )
                user_ids = [str(u.id) for u in users]

            for uid in user_ids:
                take_snapshot(uid, snap_repo)
                count += 1

            job_tracker.mark_completed(job.job_id, {"users_processed": count})
        except Exception as exc:
            job_tracker.mark_failed(job.job_id, str(exc))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    audit.log(
        actor=admin,
        action="job_trigger",
        target_type="job",
        target_id=job.job_id,
        details={"job_type": "snapshot-portfolio"},
        ip_address=request.client.host if request.client else None,
    )

    return success_response(
        data={"job_id": job.job_id, "status": "started", "type": "snapshot-portfolio"}
    )


# ── Catalog seed job (F213-T04) ──────────────────────────────────────


@router.post("/jobs/catalog-seed")
def trigger_catalog_seed(
    request: Request,
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
):
    """Seed the card catalog from Scryfall bulk data (admin only).

    Downloads the latest Scryfall default_cards file and seeds the DB.
    Runs in a background thread. Returns 409 if already running.
    """
    import tempfile
    import threading

    from src.config import get_db_url

    if job_tracker.is_running("catalog-seed"):
        raise api_error(409, ErrorCode.RESOURCE_CONFLICT, "Catalog seed is already running")

    job = job_tracker.start("catalog-seed")
    db_url = get_db_url()

    def _run():
        from src.catalog.scryfall import download_bulk_data
        from src.catalog.seeder import seed_catalog

        try:
            job_tracker.mark_running(job.job_id)
            with tempfile.TemporaryDirectory() as tmp_dir:
                bulk_path = download_bulk_data(tmp_dir)
                result = seed_catalog(db_url=db_url, bulk_path=bulk_path)
            job_tracker.mark_completed(
                job.job_id,
                {
                    "cards_inserted": result.cards_inserted,
                    "cards_updated": result.cards_updated,
                    "cards_skipped": result.cards_skipped,
                },
            )
        except Exception as exc:
            job_tracker.mark_failed(job.job_id, str(exc))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    audit.log(
        actor=admin,
        action="job_trigger",
        target_type="job",
        target_id=job.job_id,
        details={"job_type": "catalog-seed"},
        ip_address=request.client.host if request.client else None,
    )

    return success_response(
        data={"job_id": job.job_id, "status": "started", "type": "catalog-seed"}
    )


# ── Banlist sync job (F213-T04) ──────────────────────────────────────


@router.post("/jobs/banlist-sync")
def trigger_banlist_sync(
    request: Request,
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
):
    """Sync card legalities from Scryfall banlist data (admin only).

    Downloads Scryfall bulk data and updates card_legalities + legality_history.
    Runs in a background thread. Returns 409 if already running.
    """
    import asyncio
    import threading

    from src.config import get_db_url

    if job_tracker.is_running("banlist-sync"):
        raise api_error(409, ErrorCode.RESOURCE_CONFLICT, "Banlist sync is already running")

    job = job_tracker.start("banlist-sync")
    db_url = get_db_url()

    def _run():
        from src.collectors.banlist_sync import run_banlist_sync

        try:
            job_tracker.mark_running(job.job_id)
            summary = asyncio.run(run_banlist_sync(db_url=db_url))
            job_tracker.mark_completed(
                job.job_id,
                {
                    "cards_processed": summary.cards_processed,
                    "legalities_upserted": summary.legalities_upserted,
                    "changes_detected": summary.changes_detected,
                    "errors": summary.errors,
                },
            )
        except Exception as exc:
            job_tracker.mark_failed(job.job_id, str(exc))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    audit.log(
        actor=admin,
        action="job_trigger",
        target_type="job",
        target_id=job.job_id,
        details={"job_type": "banlist-sync"},
        ip_address=request.client.host if request.client else None,
    )

    return success_response(
        data={"job_id": job.job_id, "status": "started", "type": "banlist-sync"}
    )


# ── DB backup (F100-T04) ────────────────────────────────────────────


@router.get("/backup")
def download_backup(
    request: Request,
    admin: User = Depends(require_admin),
    audit: AuditService = Depends(get_audit_service),
):
    """Download a copy of the SQLite database file (admin only).

    Creates a temporary copy using SQLite's backup API to avoid
    locking issues, then streams it as a file download.
    """
    import shutil
    import sqlite3
    import tempfile
    from pathlib import Path

    from fastapi.responses import FileResponse

    from src.config import get_db_url

    db_url = get_db_url()
    if not db_url.startswith("sqlite"):
        raise HTTPException(
            400,
            "Database backup download not available for PostgreSQL. "
            "Use Neon dashboard for backups.",
        )
    # Extract file path from sqlite:/// URL
    db_path = db_url.replace("sqlite:///", "")
    if not Path(db_path).exists():
        raise HTTPException(404, "Database file not found")

    # Use SQLite backup API for a consistent copy
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp_dir = tempfile.mkdtemp()
    backup_path = Path(tmp_dir) / f"tcg_market_backup_{timestamp}.db"

    src_conn = sqlite3.connect(db_path)
    dst_conn = sqlite3.connect(str(backup_path))
    src_conn.backup(dst_conn)
    src_conn.close()
    dst_conn.close()

    file_size = backup_path.stat().st_size

    audit.log(
        actor=admin,
        action="db_backup",
        target_type="system",
        details={"file_size_bytes": file_size},
        ip_address=request.client.host if request.client else None,
    )

    return FileResponse(
        path=str(backup_path),
        filename=f"tcg_market_backup_{timestamp}.db",
        media_type="application/x-sqlite3",
        background=BackgroundTask(lambda: shutil.rmtree(tmp_dir, ignore_errors=True)),
    )


# ── Process price requests (F132-T04) ────────────────────────────────


@router.post("/jobs/process-price-requests")
def trigger_process_price_requests(
    request: Request,
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    limit: int = Query(100, ge=1, le=1000),
    delay: float = Query(2.0, ge=0.5, le=10.0),
):
    """Trigger processing of pending price requests (admin only).

    Spawns a background thread that runs the same logic as the
    ``process-price-requests`` CLI command. Only works when the server
    has access to price providers.
    """
    import asyncio
    import json
    import threading

    from src.collectors.price_request_processor import process_pending_price_requests
    from src.config import get_db_url

    # Check if there are any pending requests first
    counts = repo.count_price_requests_by_status()
    pending_count = counts.get("pending", 0)
    if pending_count == 0:
        return success_response(data={"status": "no_pending", "message": "No pending requests"})

    db_url = get_db_url()
    scan_id = repo.create_scan_run(
        "process_price_requests",
        json.dumps(
            {
                "triggered_by": admin.id,
                "limit": limit,
                "pending_count": pending_count,
            }
        ),
    )

    def _run():
        asyncio.run(
            process_pending_price_requests(
                db_url=db_url,
                limit=limit,
                delay=delay,
            )
        )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    audit.log(
        actor=admin,
        action="job_trigger",
        target_type="scan",
        target_id=str(scan_id),
        details={
            "job_type": "process_price_requests",
            "limit": limit,
            "pending_count": pending_count,
        },
        ip_address=request.client.host if request.client else None,
    )

    return success_response(
        data={
            "scan_id": scan_id,
            "status": "started",
            "pending_count": pending_count,
        }
    )


# ── Daily price snapshot (F168-T02) ──────────────────────────────────


@router.post("/jobs/snapshot-prices")
def trigger_snapshot_prices(
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
):
    """Snapshot all current prices into daily observations (admin only).

    Reads the latest known price for every card and inserts a
    ``price_observations`` row with ``source='daily_snapshot'`` for today.
    Idempotent -- running twice on the same day inserts zero new rows.
    No credit cost.
    """
    from src.collectors.price_snapshot import run_daily_snapshot

    count = run_daily_snapshot(repo)
    return success_response(data={"observations_created": count})


# ── Price request queue (F130-T05) ──────────────────────────────────


@router.get("/price-requests")
def list_price_requests(
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    status: str | None = Query(
        None, description="Filter by status: pending, processing, completed, failed"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List price update requests with optional status filter (admin only)."""
    rows, total = repo.get_price_requests(status=status, limit=limit, offset=offset)
    items = []
    for r in rows:
        card = repo.get_card_by_id(r.card_id)
        items.append(
            {
                "id": r.id,
                "card_id": r.card_id,
                "card_name": (card.name_en if card else "Unknown"),
                "user_id": r.user_id,
                "status": r.status,
                "requested_at": r.requested_at.isoformat(),
                "processed_at": r.processed_at.isoformat() if r.processed_at else None,
                "result_price": float(r.result_price) if r.result_price else None,
                "error_message": r.error_message,
                "attempts": r.attempts,
            }
        )
    return success_response(data={"items": items, "total": total})


@router.get("/price-requests/stats")
def price_request_stats(
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
):
    """Aggregate counts of price requests by status (admin only)."""
    counts = repo.count_price_requests_by_status()
    return success_response(data=counts)

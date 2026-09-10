"""Admin router -- user management, credit adjustments, platform stats,
job triggers, DB backup, and audit log (F100)."""

from __future__ import annotations

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.background import BackgroundTask

from src.api.deps import get_audit_service, get_db, require_admin
from src.api.error_codes import ErrorCode, api_error
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


@router.post("/jobs/liga-scan")
def trigger_liga_scan(
    request: Request,
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    max_age_days: int = Query(1, ge=1),
):
    """Trigger a Liga scan for all admin collections (no credit cost)."""
    import asyncio
    import json
    import threading

    from src.collectors.admin_scan import run_admin_daily_liga_scan
    from src.config import get_db_url
    from src.services.scan_hooks import default_registry

    db_url = get_db_url()
    scan_id = repo.create_scan_run(
        "admin_liga_scan",
        json.dumps({"triggered_by": admin.id, "max_age_days": max_age_days}),
    )

    def _run():
        asyncio.run(
            run_admin_daily_liga_scan(
                db_url=db_url,
                run_id=scan_id,
                max_age_days=max_age_days,
                on_complete=default_registry.notify,
            )
        )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    audit.log(
        actor=admin,
        action="job_trigger",
        target_type="scan",
        target_id=str(scan_id),
        details={"job_type": "liga_scan", "max_age_days": max_age_days},
        ip_address=request.client.host if request.client else None,
    )

    return success_response(data={"scan_id": scan_id, "status": "pending"})


@router.post("/jobs/catalog-scan")
def trigger_catalog_scan(
    request: Request,
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    set_code: str = Query(..., min_length=2, max_length=10),
    delay: float = Query(2.0, ge=0.5, le=10.0),
):
    """Trigger a Liga price sweep for a catalog set (no credit cost)."""
    import asyncio
    import json
    import threading

    from src.collectors.liga_sweep import run_liga_sweep
    from src.config import get_db_url

    db_url = get_db_url()
    scan_id = repo.create_scan_run(
        "catalog_sweep",
        json.dumps({"triggered_by": admin.id, "set_code": set_code}),
    )

    def _run():
        asyncio.run(
            run_liga_sweep(
                db_url=db_url,
                set_filter=set_code,
                delay=delay,
                collection_only=False,
            )
        )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    audit.log(
        actor=admin,
        action="job_trigger",
        target_type="scan",
        target_id=str(scan_id),
        details={"job_type": "catalog_sweep", "set_code": set_code, "delay": delay},
        ip_address=request.client.host if request.client else None,
    )

    return success_response(data={"scan_id": scan_id, "set_code": set_code, "status": "pending"})


@router.get("/jobs/status")
def get_job_status(
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
):
    """List recent admin-triggered job runs."""
    runs = repo.list_scan_runs(limit=limit, offset=0)
    return success_response(data=runs)


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

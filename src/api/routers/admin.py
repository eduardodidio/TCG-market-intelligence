"""Admin router — user management, credit adjustments, platform stats."""

from __future__ import annotations

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import get_db, require_admin
from src.api.schemas.admin import CreateUserRequest, CreateUserResponse, CreditAdjustRequest
from src.api.schemas.envelope import success_response
from src.auth.passwords import hash_password
from src.credits.service import CreditService
from src.database.repository import Repository
from src.domain.models import User

router = APIRouter(prefix="/admin", tags=["admin"])

_INITIAL_CREDITS = 50


@router.post("/users")
def create_user(
    body: CreateUserRequest,
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
):
    """Create a new user with a temporary password (admin only).

    The temporary password is returned once and must be changed on first login.
    """
    existing = repo.get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

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
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
):
    """Soft-delete a user (sets is_active=0). Admin only. Cannot delete self."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    target = repo.get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    repo.update_user(user_id, is_active=0)
    return success_response(data={"user_id": user_id, "deleted": True})


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
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
):
    """Grant or revoke credits for a user (admin only).

    Positive amount = grant. Negative amount = revoke.
    Revoke is clamped: balance cannot go below 0.
    """
    # Verify target user exists
    target = repo.get_user_by_id(user_id)
    if not target:
        raise HTTPException(404, "User not found")

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

    return success_response(
        data={
            "user_id": user_id,
            "new_balance": balance.balance,
            "amount_applied": amount_applied,
        }
    )


@router.get("/dashboard")
def admin_dashboard(
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
):
    """Platform stats (admin only)."""
    stats = repo.get_platform_stats()
    return success_response(data=stats)


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
        raise HTTPException(status_code=404, detail="Error not found")

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

"""Credits API router — balance, history, claim-bonus."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import get_current_user, get_db
from src.api.schemas.envelope import success_response
from src.credits.constants import ADMIN_MONTHLY_GRANT, BONUS_AMOUNT
from src.credits.service import CreditService
from src.database.repository import Repository
from src.domain.models import User

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/balance")
def get_balance(
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Return current credit balance + bonus eligibility.

    For admin users, auto-claims the monthly 10k grant if eligible
    (first call of the month).
    """
    svc = CreditService(repo)
    # Auto-claim monthly admin grant (no-op for non-admins)
    balance, monthly_granted = svc.claim_monthly_admin_grant(user.id, user.is_admin)
    if not monthly_granted:
        balance = svc.get_balance(user.id)
    eligibility = svc.get_bonus_eligibility(user.id)

    # Determine if monthly grant is still available this month
    monthly_grant_available = False
    if user.is_admin:
        row = repo.ensure_credit_balance(user.id)
        if row.last_monthly_grant_at is None:
            monthly_grant_available = True
        else:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            last = row.last_monthly_grant_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            monthly_grant_available = not (last.year == now.year and last.month == now.month)

    return success_response(
        data={
            "balance": balance.balance,
            "last_bonus_at": balance.last_bonus_at,
            "bonus_eligible": eligibility["eligible"],
            "next_bonus_at": eligibility["next_eligible_at"],
            "bonus_amount": eligibility["amount"],
            "is_admin": user.is_admin,
            "monthly_grant_available": monthly_grant_available,
            "monthly_grant_amount": ADMIN_MONTHLY_GRANT if user.is_admin else 0,
        }
    )


@router.get("/history")
def get_history(
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Paginated credit transaction history."""
    svc = CreditService(repo)
    transactions = svc.get_transactions(user.id, limit=limit, offset=offset)
    return success_response(
        data={
            "transactions": [
                {
                    "id": t.id,
                    "amount": t.amount,
                    "reason": t.reason,
                    "reference_id": t.reference_id,
                    "created_at": t.created_at,
                }
                for t in transactions
            ]
        }
    )


@router.post("/claim-bonus")
def claim_bonus(
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Claim 12h bonus if eligible."""
    svc = CreditService(repo)
    balance, claimed = svc.claim_bonus(user.id)
    if not claimed:
        eligibility = svc.get_bonus_eligibility(user.id)
        raise HTTPException(
            status_code=429,
            detail={
                "code": "BONUS_NOT_READY",
                "next_eligible_at": str(eligibility["next_eligible_at"]),
            },
        )
    return success_response(data={"balance": balance.balance, "credited": BONUS_AMOUNT})

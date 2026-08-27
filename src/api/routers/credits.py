"""Credits API router — balance, history, claim-bonus."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import get_current_user, get_db
from src.api.schemas.envelope import success_response
from src.credits.constants import BONUS_AMOUNT
from src.credits.service import CreditService
from src.database.repository import Repository
from src.domain.models import User

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/balance")
def get_balance(
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Return current credit balance + bonus eligibility."""
    svc = CreditService(repo)
    balance = svc.get_balance(user.id)
    eligibility = svc.get_bonus_eligibility(user.id)
    return success_response(
        data={
            "balance": balance.balance,
            "last_bonus_at": balance.last_bonus_at,
            "bonus_eligible": eligibility["eligible"],
            "next_bonus_at": eligibility["next_eligible_at"],
            "bonus_amount": eligibility["amount"],
            "is_admin": user.is_admin,
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

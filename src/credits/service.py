"""Credit service — business logic for check/deduct/grant/claim_bonus."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.credits.constants import BONUS_AMOUNT, BONUS_INTERVAL_HOURS
from src.credits.exceptions import InsufficientCreditsError
from src.database.repository import Repository
from src.domain.models import CreditBalance, CreditTransaction


def _row_to_balance(row) -> CreditBalance:
    """Convert a CreditBalanceRow to a domain CreditBalance."""
    return CreditBalance(
        user_id=row.user_id,
        balance=row.balance,
        last_bonus_at=row.last_bonus_at,
    )


def _row_to_transaction(row) -> CreditTransaction:
    """Convert a CreditTransactionRow to a domain CreditTransaction."""
    return CreditTransaction(
        id=row.id,
        user_id=row.user_id,
        amount=row.amount,
        reason=row.reason,
        reference_id=row.reference_id,
        created_at=row.created_at,
    )


class CreditService:
    """Encapsulates all credit business logic.

    Admin exemption is NOT handled here — it is checked at the router
    level. The service always charges regardless of admin status.
    """

    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def get_balance(self, user_id: int) -> CreditBalance:
        """Get current balance, creating the row if needed."""
        row = self.repo.ensure_credit_balance(user_id)
        return _row_to_balance(row)

    def check_sufficient(self, user_id: int, cost: int) -> bool:
        """Return True if user has >= cost credits."""
        balance = self.get_balance(user_id)
        return balance.balance >= cost

    def deduct(
        self,
        user_id: int,
        cost: int,
        reason: str,
        reference_id: str | None = None,
    ) -> CreditBalance:
        """Deduct credits. Raises InsufficientCreditsError if balance < cost."""
        current = self.get_balance(user_id)
        if current.balance < cost:
            raise InsufficientCreditsError(balance=current.balance, cost=cost)
        row = self.repo.update_credit_balance(
            user_id=user_id,
            delta=-cost,
            reason=reason,
            reference_id=reference_id,
        )
        return _row_to_balance(row)

    def grant(
        self,
        user_id: int,
        amount: int,
        reason: str,
        reference_id: str | None = None,
    ) -> CreditBalance:
        """Add credits to user (admin grant, bonus, etc.)."""
        row = self.repo.update_credit_balance(
            user_id=user_id,
            delta=amount,
            reason=reason,
            reference_id=reference_id,
        )
        return _row_to_balance(row)

    def claim_bonus(self, user_id: int) -> tuple[CreditBalance, bool]:
        """Claim 12h bonus (5 credits).

        Returns (balance, was_claimed). Returns (balance, False) if
        less than 12h since last claim.
        """
        balance = self.get_balance(user_id)
        now = datetime.now(timezone.utc)

        if balance.last_bonus_at is not None:
            # Treat naive datetimes as UTC
            last = balance.last_bonus_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            cutoff = last + timedelta(hours=BONUS_INTERVAL_HOURS)
            if now < cutoff:
                return balance, False

        # Grant bonus
        self.repo.update_credit_balance(
            user_id=user_id,
            delta=BONUS_AMOUNT,
            reason="bonus_claim",
        )
        # Update last_bonus_at on the balance row
        self.repo.update_last_bonus_at(user_id, now)
        updated = self.get_balance(user_id)
        return updated, True

    def get_bonus_eligibility(self, user_id: int) -> dict:
        """Return bonus eligibility info.

        Returns:
            {eligible: bool, next_eligible_at: datetime | None, amount: int}
        """
        balance = self.get_balance(user_id)
        now = datetime.now(timezone.utc)

        if balance.last_bonus_at is None:
            return {
                "eligible": True,
                "next_eligible_at": None,
                "amount": BONUS_AMOUNT,
            }

        last = balance.last_bonus_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        next_eligible = last + timedelta(hours=BONUS_INTERVAL_HOURS)

        return {
            "eligible": now >= next_eligible,
            "next_eligible_at": next_eligible,
            "amount": BONUS_AMOUNT,
        }

    def get_transactions(
        self, user_id: int, limit: int = 50, offset: int = 0
    ) -> list[CreditTransaction]:
        """Paginated transaction history, newest first."""
        rows = self.repo.get_credit_transactions(user_id=user_id, limit=limit, offset=offset)
        return [_row_to_transaction(r) for r in rows]

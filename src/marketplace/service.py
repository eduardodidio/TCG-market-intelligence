"""Marketplace service — trade orchestration logic."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import structlog

from src.credits.exceptions import InsufficientCreditsError
from src.credits.service import CreditService
from src.database.repository import Repository
from src.marketplace.fees import calculate_trade_fee

log = structlog.get_logger()


class MarketplaceService:
    """Orchestrates the trade lifecycle: interest → accept → confirm → complete."""

    def __init__(self, repo: Repository, credit_service: CreditService) -> None:
        self.repo = repo
        self.credit_svc = credit_service

    def toggle_sharing(self, user_id: int, is_shared: bool) -> dict:
        """Toggle collection sharing. Returns sharing status."""
        row = self.repo.set_sharing(user_id=user_id, is_shared=is_shared)
        return {
            "is_shared": bool(row.is_shared),
            "share_code": row.share_code,
        }

    def get_sharing_status(self, user_id: int) -> dict:
        """Get current sharing status for a user."""
        row = self.repo.get_shared_collection(user_id=user_id)
        if row is None:
            return {"is_shared": False, "share_code": None}
        return {
            "is_shared": bool(row.is_shared),
            "share_code": row.share_code,
        }

    def get_listings(
        self,
        limit: int = 20,
        offset: int = 0,
        set_code: str | None = None,
        search: str | None = None,
        exclude_user_id: int | None = None,
    ) -> list[dict]:
        """Browse marketplace listings (anonymized cards from shared collections)."""
        return self.repo.list_marketplace_entries(
            limit=limit,
            offset=offset,
            set_code=set_code,
            search=search,
            exclude_user_id=exclude_user_id,
        )

    def express_interest(
        self,
        buyer_user_id: int,
        share_code: str,
        entry_id: int,
        message: str | None = None,
    ) -> dict:
        """Express interest in trading a card.

        Returns the created trade interest details.
        Raises ValueError for self-trade or invalid share_code/entry.
        """
        # Look up the shared collection
        shared = self.repo.get_shared_collection_by_code(share_code)
        if shared is None:
            raise ValueError("Shared collection not found")

        seller_user_id = shared.user_id

        # Prevent self-trading
        if buyer_user_id == seller_user_id:
            raise ValueError("Cannot trade with yourself")

        # Verify the entry belongs to the seller
        entry = self.repo.get_collection_entry(entry_id)
        if entry is None:
            raise ValueError("Collection entry not found")
        if str(entry.user_id) != str(seller_user_id):
            raise ValueError("Entry does not belong to this shared collection")

        # Get card price for fee calculation
        card_price: Decimal | None = None
        if entry.card_id is not None:
            prices = self.repo.get_latest_prices_batch([entry.card_id])
            obs = prices.get(entry.card_id)
            if obs is not None:
                card_price = obs.median_price

        fee = calculate_trade_fee(card_price)

        interest = self.repo.create_trade_interest(
            buyer_user_id=buyer_user_id,
            seller_user_id=seller_user_id,
            collection_entry_id=entry_id,
            message=message,
            estimated_fee=fee,
            card_price_at_interest=card_price,
        )

        return {
            "id": interest.id,
            "status": interest.status,
            "estimated_fee": fee,
            "card_price": card_price,
        }

    def respond_to_interest(
        self,
        interest_id: int,
        user_id: int,
        action: str,
    ) -> dict:
        """Seller responds to a trade interest (accept or reject).

        On accept, creates a TradeAgreement row.
        Raises ValueError for invalid action or unauthorized access.
        """
        interest = self.repo.get_trade_interest(interest_id)
        if interest is None:
            raise ValueError("Trade interest not found")

        # Only seller can respond
        if interest.seller_user_id != user_id:
            raise PermissionError("Only the seller can respond to this interest")

        if interest.status != "pending":
            raise ValueError(f"Cannot respond to interest in status: {interest.status}")

        if action not in ("accept", "reject"):
            raise ValueError("Action must be 'accept' or 'reject'")

        if action == "reject":
            self.repo.update_trade_interest_status(interest_id, "rejected")
            return {"id": interest_id, "status": "rejected"}

        # Accept: update status and create agreement
        self.repo.update_trade_interest_status(interest_id, "accepted")
        agreement = self.repo.create_trade_agreement(interest_id)

        return {
            "id": interest_id,
            "status": "accepted",
            "agreement_id": agreement.id,
        }

    def confirm_agreement(
        self,
        interest_id: int,
        user_id: int,
    ) -> dict:
        """Confirm trade agreement (buyer or seller).

        When both confirm: check credits, deduct from both, reveal emails.
        Returns trade detail with email if completed.
        """
        interest = self.repo.get_trade_interest(interest_id)
        if interest is None:
            raise ValueError("Trade interest not found")

        if interest.status != "accepted":
            raise ValueError(f"Cannot confirm interest in status: {interest.status}")

        # Verify user is a participant
        is_buyer = interest.buyer_user_id == user_id
        is_seller = interest.seller_user_id == user_id
        if not is_buyer and not is_seller:
            raise PermissionError("You are not a participant in this trade")

        agreement = self.repo.get_trade_agreement_by_interest(interest_id)
        if agreement is None:
            raise ValueError("Trade agreement not found")

        # Atomic confirm — UPDATE WHERE field=0 prevents double-confirm race
        field = "buyer_confirmed" if is_buyer else "seller_confirmed"
        updated = self.repo.atomic_confirm_agreement(agreement.id, field)
        if not updated:
            raise ValueError("You have already confirmed")

        # Refresh agreement to check if both confirmed
        agreement = self.repo.get_trade_agreement(agreement.id)

        if agreement.buyer_confirmed and agreement.seller_confirmed:
            return self._complete_trade(interest, agreement)

        return {
            "id": interest_id,
            "status": "accepted",
            "my_confirmed": True,
            "both_confirmed": False,
        }

    def _complete_trade(self, interest, agreement) -> dict:
        """Finalize trade: charge credits, reveal emails, mark completed.

        Idempotency: if completed_at is already set, returns the completed
        state without re-charging. This prevents double-spend if two
        concurrent confirm_agreement calls both reach this method.
        """
        # Idempotency guard — already completed
        if agreement.completed_at is not None:
            log.warning("trade_already_completed", agreement_id=agreement.id)
            return {
                "id": interest.id,
                "status": "completed",
                "my_confirmed": True,
                "both_confirmed": True,
                "fee_charged": agreement.buyer_fee_charged,
                "buyer_email": self._get_user_email(interest.buyer_user_id),
                "seller_email": self._get_user_email(interest.seller_user_id),
            }

        fee = interest.estimated_fee

        # Check both have sufficient credits
        buyer_ok = self.credit_svc.check_sufficient(interest.buyer_user_id, fee)
        seller_ok = self.credit_svc.check_sufficient(interest.seller_user_id, fee)

        if not buyer_ok:
            raise InsufficientCreditsError(
                balance=self.credit_svc.get_balance(interest.buyer_user_id).balance,
                cost=fee,
            )
        if not seller_ok:
            raise InsufficientCreditsError(
                balance=self.credit_svc.get_balance(interest.seller_user_id).balance,
                cost=fee,
            )

        ref = str(interest.id)

        # Deduct from buyer first
        self.credit_svc.deduct(interest.buyer_user_id, fee, "trade_fee", reference_id=ref)

        # Deduct from seller — compensate buyer if this fails
        try:
            self.credit_svc.deduct(interest.seller_user_id, fee, "trade_fee", reference_id=ref)
        except (InsufficientCreditsError, ValueError):
            # Compensate buyer deduction
            self.credit_svc.grant(
                interest.buyer_user_id,
                fee,
                "trade_fee_refund",
                reference_id=ref,
            )
            log.warning(
                "trade_seller_deduct_failed_buyer_refunded",
                interest_id=interest.id,
                fee=fee,
            )
            raise InsufficientCreditsError(
                balance=self.credit_svc.get_balance(interest.seller_user_id).balance,
                cost=fee,
            )

        # Mark agreement as completed
        now = datetime.now()
        self.repo.update_trade_agreement(
            agreement.id,
            buyer_fee_charged=fee,
            seller_fee_charged=fee,
            completed_at=now,
        )

        # Mark interest as completed
        self.repo.update_trade_interest_status(interest.id, "completed")

        # Get emails for reveal
        buyer_email = self._get_user_email(interest.buyer_user_id)
        seller_email = self._get_user_email(interest.seller_user_id)

        return {
            "id": interest.id,
            "status": "completed",
            "my_confirmed": True,
            "both_confirmed": True,
            "fee_charged": fee,
            "buyer_email": buyer_email,
            "seller_email": seller_email,
        }

    def _get_user_email(self, user_id: int) -> str | None:
        """Look up user email by ID."""
        user = self.repo.get_user_by_id(user_id)
        return user.email if user else None

    def get_my_trades(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Get user's trade history with role annotation."""
        trades = self.repo.get_user_trades(user_id, limit=limit, offset=offset)
        result = []
        for t in trades:
            is_buyer = t.buyer_user_id == user_id
            counterparty_id = t.seller_user_id if is_buyer else t.buyer_user_id

            # Get counterparty share code
            counterparty_shared = self.repo.get_shared_collection(counterparty_id)
            counterparty_code = counterparty_shared.share_code if counterparty_shared else None

            # Get card name from collection entry
            entry = self.repo.get_collection_entry(t.collection_entry_id)
            card_name = entry.name_en if entry else "Unknown Card"

            # Get counterparty email if trade is completed
            counterparty_email = None
            if t.status == "completed":
                counterparty_email = self._get_user_email(counterparty_id)

            result.append(
                {
                    "id": t.id,
                    "card_name": card_name,
                    "set_code": entry.set_code if entry else "",
                    "collector_number": entry.collector_number if entry else "",
                    "counterparty_share_code": counterparty_code,
                    "status": t.status,
                    "estimated_fee": t.estimated_fee,
                    "my_role": "buyer" if is_buyer else "seller",
                    "counterparty_email": counterparty_email,
                    "created_at": t.created_at,
                }
            )
        return result

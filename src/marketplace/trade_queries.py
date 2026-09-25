"""Filtered/sorted read queries for the trades area (F174).

Kept separate from ``src.database.repository.Repository`` because that
module is shared with parallel batch features and must not be touched here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String as SAString
from sqlalchemy import case, func, select
from sqlalchemy import cast as sa_cast
from sqlalchemy.orm import Session

from src.database.models import (
    CardRow,
    PriceObservationRow,
    SharedCollectionRow,
    UserCollectionRow,
)
from src.marketplace.fees import calculate_trade_fee

if TYPE_CHECKING:
    from src.database.repository import Repository

LISTING_SORTS = {"name", "set", "number", "price"}
DUPLICATE_SORTS = {"quantity", "name", "set", "number", "price"}
SORT_DIRS = {"asc", "desc"}


def _liga_price_expr():
    """Correlated scalar subquery: latest Liga price (normal or foil)."""
    liga_ext = func.concat("liga_", sa_cast(UserCollectionRow.card_id, SAString))
    liga_ext_foil = func.concat(liga_ext, "_foil")
    return (
        select(PriceObservationRow.median_price)
        .where(
            PriceObservationRow.source == "liga",
            (PriceObservationRow.external_id == liga_ext)
            | (PriceObservationRow.external_id == liga_ext_foil),
        )
        .order_by(PriceObservationRow.observed_at.desc())
        .limit(1)
        .correlate(UserCollectionRow)
        .scalar_subquery()
    )


class TradeQueries:
    """Filtered/sorted read queries for the trades area (F174)."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.engine = repo.engine

    def _apply_sort(self, stmt, sort_by: str, sort_dir: str, sort_columns: set[str]):
        if sort_by not in sort_columns:
            raise ValueError(f"Unknown sort_by: {sort_by!r}")
        if sort_dir not in SORT_DIRS:
            raise ValueError(f"Unknown sort_dir: {sort_dir!r}")

        if sort_by == "price":
            sort_price = _liga_price_expr()
            null_flag = case((sort_price.is_(None), 1), else_=0)
            sort_expr = sort_price.desc() if sort_dir == "desc" else sort_price.asc()
            return stmt.order_by(null_flag, sort_expr, UserCollectionRow.id.asc())

        if sort_by == "quantity":
            col = UserCollectionRow.quantity
        elif sort_by == "set":
            col = UserCollectionRow.set_code
        elif sort_by == "number":
            col = UserCollectionRow.collector_number
        else:
            col = func.coalesce(UserCollectionRow.name_en, "")

        sort_expr = col.desc() if sort_dir == "desc" else col.asc()
        return stmt.order_by(sort_expr, UserCollectionRow.id.asc())

    def list_listings(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        set_code: str | None = None,
        search: str | None = None,
        exclude_user_id: int | None = None,
        share_code: str | None = None,
        sort_by: str = "name",
        sort_dir: str = "asc",
    ) -> list[dict]:
        """List shared-collection cards for the marketplace."""
        with Session(self.engine) as session:
            stmt = (
                select(
                    SharedCollectionRow.share_code,
                    UserCollectionRow.id.label("entry_id"),
                    UserCollectionRow.name_en,
                    UserCollectionRow.name_pt,
                    UserCollectionRow.set_code,
                    UserCollectionRow.collector_number,
                    UserCollectionRow.rarity,
                    UserCollectionRow.quantity,
                    UserCollectionRow.card_id,
                )
                .join(
                    UserCollectionRow,
                    sa_cast(SharedCollectionRow.user_id, SAString) == UserCollectionRow.user_id,
                )
                .where(SharedCollectionRow.is_shared == 1)
            )

            if share_code is not None:
                stmt = stmt.where(SharedCollectionRow.share_code == share_code)

            if exclude_user_id is not None:
                stmt = stmt.where(SharedCollectionRow.user_id != exclude_user_id)

            if set_code:
                stmt = stmt.where(func.lower(UserCollectionRow.set_code) == set_code.lower())

            search = (search or "").strip()
            if search:
                pattern = f"%{search}%"
                stmt = stmt.where(
                    UserCollectionRow.name_en.ilike(pattern)
                    | UserCollectionRow.name_pt.ilike(pattern)
                )

            stmt = self._apply_sort(stmt, sort_by, sort_dir, LISTING_SORTS)
            stmt = stmt.limit(limit).offset(offset)

            rows = session.execute(stmt).all()

            card_ids = [r.card_id for r in rows if r.card_id is not None]
            prices: dict = {}
            if card_ids:
                prices = self.repo.get_latest_prices_batch(card_ids)

            result = []
            for r in rows:
                price = None
                if r.card_id is not None:
                    obs = prices.get(r.card_id)
                    if obs is not None:
                        price = obs.median_price

                result.append(
                    {
                        "share_code": r.share_code,
                        "entry_id": r.entry_id,
                        "card_name_en": r.name_en or "",
                        "card_name_pt": r.name_pt,
                        "set_code": r.set_code,
                        "collector_number": r.collector_number,
                        "rarity": r.rarity,
                        "quantity": r.quantity,
                        "latest_price": price,
                        "estimated_fee": calculate_trade_fee(price),
                    }
                )
            return result

    def list_listing_sets(self, *, exclude_user_id: int | None = None) -> list[dict]:
        """Return set facets for the marketplace listings."""
        with Session(self.engine) as session:
            stmt = (
                select(
                    UserCollectionRow.set_code,
                    func.max(UserCollectionRow.set_name_en),
                    func.count(UserCollectionRow.id),
                )
                .select_from(SharedCollectionRow)
                .join(
                    UserCollectionRow,
                    sa_cast(SharedCollectionRow.user_id, SAString) == UserCollectionRow.user_id,
                )
                .where(SharedCollectionRow.is_shared == 1)
            )

            if exclude_user_id is not None:
                stmt = stmt.where(SharedCollectionRow.user_id != exclude_user_id)

            stmt = stmt.group_by(UserCollectionRow.set_code).order_by(UserCollectionRow.set_code)

            rows = session.execute(stmt).all()
            return [
                {"set_code": r[0], "set_name": r[1], "count": r[2]}
                for r in rows
            ]

    def list_duplicates(
        self,
        user_id: int | str,
        *,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
        set_code: str | None = None,
        sort_by: str = "quantity",
        sort_dir: str = "desc",
    ) -> tuple[list[dict], int]:
        """Return collection entries with quantity > 1, filtered/sorted, and total count."""
        with Session(self.engine) as session:
            base = (
                select(
                    UserCollectionRow.card_id,
                    UserCollectionRow.name_en,
                    UserCollectionRow.name_pt,
                    UserCollectionRow.set_code,
                    UserCollectionRow.collector_number,
                    UserCollectionRow.quantity,
                    UserCollectionRow.quality,
                    CardRow.image_uri,
                    CardRow.rarity,
                )
                .outerjoin(CardRow, UserCollectionRow.card_id == CardRow.id)
                .where(
                    UserCollectionRow.user_id == str(user_id),
                    UserCollectionRow.quantity > 1,
                    UserCollectionRow.card_id.isnot(None),
                )
            )

            if set_code:
                base = base.where(func.lower(UserCollectionRow.set_code) == set_code.lower())

            search = (search or "").strip()
            if search:
                pattern = f"%{search}%"
                base = base.where(
                    UserCollectionRow.name_en.ilike(pattern)
                    | UserCollectionRow.name_pt.ilike(pattern)
                )

            total = session.scalar(select(func.count()).select_from(base.subquery()))

            base = self._apply_sort(base, sort_by, sort_dir, DUPLICATE_SORTS)
            rows = session.execute(base.limit(limit).offset(offset)).all()

            return [
                {
                    "card_id": r.card_id,
                    "name_en": r.name_en,
                    "name_pt": r.name_pt,
                    "set_code": r.set_code,
                    "collector_number": r.collector_number,
                    "quantity": r.quantity,
                    "surplus": r.quantity - 1,
                    "quality": r.quality,
                    "image_uri": r.image_uri,
                    "rarity": r.rarity,
                }
                for r in rows
            ], total or 0

    def list_duplicate_sets(self, user_id: int | str) -> list[dict]:
        """Return set facets for a user's duplicates (quantity>1, card_id not null)."""
        with Session(self.engine) as session:
            stmt = (
                select(
                    UserCollectionRow.set_code,
                    func.max(UserCollectionRow.set_name_en),
                    func.count(UserCollectionRow.id),
                )
                .where(
                    UserCollectionRow.user_id == str(user_id),
                    UserCollectionRow.quantity > 1,
                    UserCollectionRow.card_id.isnot(None),
                )
                .group_by(UserCollectionRow.set_code)
                .order_by(UserCollectionRow.set_code)
            )

            rows = session.execute(stmt).all()
            return [
                {"set_code": r[0], "set_name": r[1], "count": r[2]}
                for r in rows
            ]

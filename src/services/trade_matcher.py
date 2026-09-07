"""Trade matcher service (F110-T04).

Finds potential trade partners by cross-referencing wishlists with
duplicate cards across users with shared collections.
"""

from __future__ import annotations

import structlog
from sqlalchemy import String as SAString
from sqlalchemy import cast as sa_cast
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import (
    CardRow,
    SharedCollectionRow,
    UserCollectionRow,
    UserRow,
    WishlistRow,
)
from src.database.repository import Repository

log = structlog.get_logger()


def find_trade_matches(
    user_id: int,
    repo: Repository,
    limit: int = 20,
) -> list[dict]:
    """Find users whose duplicates match the given user's wishlist.

    Returns a list of trade match dicts, ranked by number of matching cards.
    Only considers users with is_shared=1.
    """
    with Session(repo.engine) as session:
        # Get user's active wishlist card_ids + max_price
        wishlist_items = session.execute(
            select(WishlistRow.card_id, WishlistRow.max_price).where(
                WishlistRow.user_id == user_id,
                WishlistRow.is_acquired == 0,
            )
        ).all()

        if not wishlist_items:
            return []

        wishlist_card_ids = [w.card_id for w in wishlist_items]
        max_price_map = {w.card_id: w.max_price for w in wishlist_items}

        # Find other users who have those cards with quantity > 1
        # AND whose collection is shared
        query = (
            select(
                UserCollectionRow.card_id,
                UserCollectionRow.quantity,
                SharedCollectionRow.share_code,
                sa_cast(SharedCollectionRow.user_id, SAString).label("partner_user_id_str"),
                SharedCollectionRow.user_id.label("partner_user_id"),
                UserRow.display_name,
                CardRow.name_en,
                CardRow.set_code,
                CardRow.image_uri,
            )
            .join(
                SharedCollectionRow,
                sa_cast(SharedCollectionRow.user_id, SAString) == UserCollectionRow.user_id,
            )
            .join(UserRow, UserRow.id == SharedCollectionRow.user_id)
            .outerjoin(CardRow, CardRow.id == UserCollectionRow.card_id)
            .where(
                UserCollectionRow.card_id.in_(wishlist_card_ids),
                UserCollectionRow.quantity > 1,
                UserCollectionRow.user_id != str(user_id),
                SharedCollectionRow.is_shared == 1,
            )
        )

        rows = session.execute(query).all()

        if not rows:
            return []

        # Group by partner
        partners: dict[str, dict] = {}
        for r in rows:
            code = r.share_code
            if code not in partners:
                partners[code] = {
                    "partner_name": r.display_name or "Anonymous",
                    "share_code": code,
                    "matched_cards": [],
                }
            partners[code]["matched_cards"].append(
                {
                    "card_id": r.card_id,
                    "name_en": r.name_en or "Unknown",
                    "set_code": r.set_code,
                    "image_uri": r.image_uri,
                    "partner_quantity": r.quantity,
                    "your_max_price": (
                        float(max_price_map.get(r.card_id))
                        if max_price_map.get(r.card_id) is not None
                        else None
                    ),
                }
            )

        # Build result, ranked by match count
        result = []
        for data in partners.values():
            data["matching_card_count"] = len(data["matched_cards"])
            result.append(data)

        result.sort(key=lambda x: x["matching_card_count"], reverse=True)
        return result[:limit]


def find_reverse_matches(
    user_id: int,
    repo: Repository,
    limit: int = 20,
) -> list[dict]:
    """Find users whose wishlists match the given user's duplicates.

    "Who wants my duplicate cards?"
    Only considers users with shared collections (is_shared=1).
    """
    with Session(repo.engine) as session:
        # Get user's duplicate card_ids
        duplicate_map = repo.get_user_duplicate_card_ids(user_id)
        if not duplicate_map:
            return []

        duplicate_card_ids = list(duplicate_map.keys())

        # Find other users whose wishlists contain these card_ids
        # and who have shared collections
        query = (
            select(
                WishlistRow.card_id,
                WishlistRow.user_id.label("wisher_user_id"),
                WishlistRow.max_price,
                SharedCollectionRow.share_code,
                UserRow.display_name,
                CardRow.name_en,
                CardRow.set_code,
                CardRow.image_uri,
            )
            .join(SharedCollectionRow, SharedCollectionRow.user_id == WishlistRow.user_id)
            .join(UserRow, UserRow.id == WishlistRow.user_id)
            .outerjoin(CardRow, CardRow.id == WishlistRow.card_id)
            .where(
                WishlistRow.card_id.in_(duplicate_card_ids),
                WishlistRow.is_acquired == 0,
                WishlistRow.user_id != user_id,
                SharedCollectionRow.is_shared == 1,
            )
        )

        rows = session.execute(query).all()

        if not rows:
            return []

        # Group by wisher
        partners: dict[str, dict] = {}
        for r in rows:
            code = r.share_code
            if code not in partners:
                partners[code] = {
                    "partner_name": r.display_name or "Anonymous",
                    "share_code": code,
                    "matched_cards": [],
                }
            partners[code]["matched_cards"].append(
                {
                    "card_id": r.card_id,
                    "name_en": r.name_en or "Unknown",
                    "set_code": r.set_code,
                    "image_uri": r.image_uri,
                    "partner_quantity": duplicate_map.get(r.card_id, 0),
                    "your_max_price": float(r.max_price) if r.max_price is not None else None,
                }
            )

        result = []
        for data in partners.values():
            data["matching_card_count"] = len(data["matched_cards"])
            result.append(data)

        result.sort(key=lambda x: x["matching_card_count"], reverse=True)
        return result[:limit]

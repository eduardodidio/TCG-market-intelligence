"""Reward tiers and idempotent Treasure crediting for achievements (F179-T02)."""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import AchievementRow, CreditBalanceRow, CreditTransactionRow

logger = structlog.get_logger(__name__)

ACHIEVEMENT_REWARD_REASON = "achievement_reward"

REWARD_TIERS: dict[str, int] = {
    "common": 50,
    "uncommon": 100,
    "rare": 250,
    "mythic": 500,
    "legendary": 1000,
}

ACHIEVEMENT_TIERS: dict[str, str] = {
    "first_card": "common",
    "deck_builder": "common",
    "scanner": "common",
    "price_watcher": "common",
    "collector_10": "uncommon",
    "early_adopter": "uncommon",
    "collector_50": "rare",
    "treasure_hunter": "rare",
    "collector_100": "mythic",
    "collector_500": "legendary",
    "set_master": "legendary",
}


def get_tier(key: str) -> str | None:
    """Return the reward tier for an achievement key, or None if unknown."""
    return ACHIEVEMENT_TIERS.get(key)


def get_reward(key: str) -> int:
    """Return the Treasure reward for an achievement key, or 0 if unknown."""
    tier = ACHIEVEMENT_TIERS.get(key)
    if tier is None:
        return 0
    return REWARD_TIERS.get(tier, 0)


def reference_id_for(key: str) -> str:
    """Return the ledger reference_id for an achievement key."""
    return f"achievement:{key}"


def credited_keys(session: Session, user_id: int) -> set[str]:
    """Return achievement keys already credited (have a ledger row) for a user."""
    rows = session.execute(
        select(CreditTransactionRow.reference_id).where(
            CreditTransactionRow.user_id == user_id,
            CreditTransactionRow.reason == ACHIEVEMENT_REWARD_REASON,
        )
    ).all()
    keys = set()
    prefix = "achievement:"
    for (reference_id,) in rows:
        if reference_id and reference_id.startswith(prefix):
            keys.add(reference_id[len(prefix) :])
    return keys


def credit_reward_in_session(session: Session, user_id: int, key: str) -> int:
    """Credit the Treasure reward for one achievement, once. Caller commits."""
    amount = get_reward(key)
    if amount <= 0:
        return 0

    ref = reference_id_for(key)

    # Lock the balance row BEFORE checking the ledger (ADR 0020 §2). A concurrent
    # transaction crediting the same achievement blocks here until it commits, and
    # the re-check below (READ COMMITTED: new snapshot per statement) then sees its
    # ledger row, so the reward is never credited twice.
    bal = session.execute(
        select(CreditBalanceRow).where(CreditBalanceRow.user_id == user_id).with_for_update()
    ).scalar_one_or_none()

    exists = session.execute(
        select(CreditTransactionRow.id)
        .where(
            CreditTransactionRow.user_id == user_id,
            CreditTransactionRow.reason == ACHIEVEMENT_REWARD_REASON,
            CreditTransactionRow.reference_id == ref,
        )
        .limit(1)
    ).first()
    if exists:
        return 0

    if bal is None:
        bal = CreditBalanceRow(user_id=user_id, balance=0)
        session.add(bal)
        session.flush()

    bal.balance += amount
    session.add(
        CreditTransactionRow(
            user_id=user_id,
            amount=amount,
            reason=ACHIEVEMENT_REWARD_REASON,
            reference_id=ref,
        )
    )
    return amount


def backfill_user_rewards_in_session(session: Session, user_id: int) -> int:
    """Credit rewards for every unlocked achievement of a user. Caller commits."""
    keys = session.execute(
        select(AchievementRow.achievement_key).where(AchievementRow.user_id == user_id)
    ).scalars().all()

    total = 0
    for key in keys:
        total += credit_reward_in_session(session, user_id, key)
    return total


def backfill_all_rewards(repo, *, dry_run: bool = False, user_id: int | None = None) -> dict:
    """Backfill Treasure rewards for previously-unlocked achievements, all users or one."""
    with Session(repo.engine) as session:
        query = select(AchievementRow.user_id).distinct()
        if user_id is not None:
            query = query.where(AchievementRow.user_id == user_id)
        user_ids = session.execute(query).scalars().all()

    result = {
        "users": len(user_ids),
        "credited_users": 0,
        "credited_rows": 0,
        "total_tokens": 0,
        "errors": 0,
    }

    for uid in user_ids:
        try:
            with Session(repo.engine) as session:
                keys = (
                    session.execute(
                        select(AchievementRow.achievement_key).where(
                            AchievementRow.user_id == uid
                        )
                    )
                    .scalars()
                    .all()
                )

                credited_rows = 0
                total_tokens = 0
                for key in keys:
                    amount = credit_reward_in_session(session, uid, key)
                    if amount > 0:
                        credited_rows += 1
                        total_tokens += amount

                if dry_run:
                    session.rollback()
                else:
                    session.commit()

                if credited_rows > 0:
                    result["credited_users"] += 1
                    result["credited_rows"] += credited_rows
                    result["total_tokens"] += total_tokens
        except Exception:
            logger.exception("achievement_rewards.backfill_user_failed", user_id=uid)
            result["errors"] += 1

    return result

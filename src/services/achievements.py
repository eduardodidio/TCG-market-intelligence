"""Achievement definitions and checker service (F109)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.database.models import (
    AchievementRow,
    CreditTransactionRow,
    DeckRow,
    ScanRunRow,
    UserCollectionRow,
)
from src.database.repository import Repository

# PriceAlertRow may not exist yet (F106); import conditionally
try:
    from src.database.models import PriceAlertRow  # type: ignore[attr-defined]
except ImportError:
    PriceAlertRow = None  # type: ignore[assignment, misc]

ACHIEVEMENT_DEFINITIONS: list[dict] = [
    {
        "key": "first_card",
        "title_en": "First Card",
        "title_pt": "Primeira Carta",
        "description_en": "Add your first card to collection",
        "description_pt": "Adicione sua primeira carta",
        "icon": "card",
    },
    {
        "key": "deck_builder",
        "title_en": "Deck Builder",
        "title_pt": "Construtor de Decks",
        "description_en": "Create your first deck",
        "description_pt": "Crie seu primeiro deck",
        "icon": "deck",
    },
    {
        "key": "scanner",
        "title_en": "Scanner",
        "title_pt": "Scanner",
        "description_en": "Complete your first price scan",
        "description_pt": "Complete seu primeiro scan",
        "icon": "scan",
    },
    {
        "key": "collector_10",
        "title_en": "Collector",
        "title_pt": "Colecionador",
        "description_en": "Own 10 unique cards",
        "description_pt": "Tenha 10 cartas unicas",
        "icon": "collection",
    },
    {
        "key": "collector_50",
        "title_en": "Avid Collector",
        "title_pt": "Colecionador Avido",
        "description_en": "Own 50 unique cards",
        "description_pt": "Tenha 50 cartas unicas",
        "icon": "collection",
    },
    {
        "key": "collector_100",
        "title_en": "Serious Collector",
        "title_pt": "Colecionador Serio",
        "description_en": "Own 100 unique cards",
        "description_pt": "Tenha 100 cartas unicas",
        "icon": "collection",
    },
    {
        "key": "collector_500",
        "title_en": "Master Collector",
        "title_pt": "Mestre Colecionador",
        "description_en": "Own 500 unique cards",
        "description_pt": "Tenha 500 cartas unicas",
        "icon": "collection",
    },
    {
        "key": "set_master",
        "title_en": "Set Master",
        "title_pt": "Mestre do Set",
        "description_en": "Complete an entire set",
        "description_pt": "Complete um set inteiro",
        "icon": "trophy",
    },
    {
        "key": "price_watcher",
        "title_en": "Price Watcher",
        "title_pt": "Observador de Precos",
        "description_en": "Set your first price alert",
        "description_pt": "Crie seu primeiro alerta",
        "icon": "alert",
    },
    {
        "key": "treasure_hunter",
        "title_en": "Treasure Hunter",
        "title_pt": "Cacador de Tesouros",
        "description_en": "Claim the bonus 5 times",
        "description_pt": "Resgate o bonus 5 vezes",
        "icon": "treasure",
    },
    {
        "key": "early_adopter",
        "title_en": "Early Adopter",
        "title_pt": "Pioneiro",
        "description_en": "Account created before official launch",
        "description_pt": "Conta criada antes do lancamento",
        "icon": "star",
    },
]

# Lookup by key for quick access
_DEFINITIONS_BY_KEY: dict[str, dict] = {d["key"]: d for d in ACHIEVEMENT_DEFINITIONS}

# Early adopter cutoff date (configurable; accounts before this qualify)
EARLY_ADOPTER_CUTOFF = datetime(2027, 1, 1)


def get_definition(key: str) -> dict | None:
    """Return achievement definition by key."""
    return _DEFINITIONS_BY_KEY.get(key)


def _get_user_stats(user_id: int, session: Session) -> dict:
    """Gather lightweight stats for achievement checks."""
    user_id_str = str(user_id)

    # Card count (unique entries in collection)
    card_count = (
        session.execute(
            select(func.count())
            .select_from(UserCollectionRow)
            .where(UserCollectionRow.user_id == user_id_str)
        ).scalar()
        or 0
    )

    # Deck count
    deck_count = (
        session.execute(
            select(func.count()).select_from(DeckRow).where(DeckRow.user_id == user_id_str)
        ).scalar()
        or 0
    )

    # Completed scan count
    scan_count = (
        session.execute(
            select(func.count()).select_from(ScanRunRow).where(ScanRunRow.status == "completed")
        ).scalar()
        or 0
    )

    # Alert count (PriceAlertRow may not exist in older DB schemas)
    alert_count = 0
    if PriceAlertRow is not None:
        alert_count = (
            session.execute(
                select(func.count())
                .select_from(PriceAlertRow)
                .where(PriceAlertRow.user_id == user_id)
            ).scalar()
            or 0
        )

    # Bonus claim count (credit transactions with reason='bonus')
    bonus_claims = (
        session.execute(
            select(func.count())
            .select_from(CreditTransactionRow)
            .where(
                CreditTransactionRow.user_id == user_id,
                CreditTransactionRow.reason == "bonus",
            )
        ).scalar()
        or 0
    )

    # User created_at (for early adopter)
    from src.database.models import UserRow

    user_row = session.execute(select(UserRow.created_at).where(UserRow.id == user_id)).scalar()

    return {
        "card_count": card_count,
        "deck_count": deck_count,
        "scan_count": scan_count,
        "alert_count": alert_count,
        "bonus_claims": bonus_claims,
        "user_created_at": user_row,
    }


def _evaluate_achievements(stats: dict) -> list[str]:
    """Return list of achievement keys that should be unlocked given stats."""
    earned: list[str] = []

    if stats["card_count"] >= 1:
        earned.append("first_card")
    if stats["card_count"] >= 10:
        earned.append("collector_10")
    if stats["card_count"] >= 50:
        earned.append("collector_50")
    if stats["card_count"] >= 100:
        earned.append("collector_100")
    if stats["card_count"] >= 500:
        earned.append("collector_500")
    if stats["deck_count"] >= 1:
        earned.append("deck_builder")
    if stats["scan_count"] >= 1:
        earned.append("scanner")
    if stats["alert_count"] >= 1:
        earned.append("price_watcher")
    if stats["bonus_claims"] >= 5:
        earned.append("treasure_hunter")
    if stats["user_created_at"] and stats["user_created_at"] < EARLY_ADOPTER_CUTOFF:
        earned.append("early_adopter")

    # set_master is checked separately via set-completion endpoint,
    # but we include it if any set is 100% complete.
    # We skip the heavy query here — set_master is granted externally.

    return earned


def check_achievements(user_id: int, repo: Repository) -> list[str]:
    """Check and grant achievements for a user.

    Returns list of *newly* unlocked achievement keys.
    """
    with Session(repo.engine) as session:
        # Get current stats
        stats = _get_user_stats(user_id, session)

        # Evaluate which achievements should be earned
        earned_keys = _evaluate_achievements(stats)

        if not earned_keys:
            return []

        # Get already unlocked achievements
        existing = set(
            session.execute(
                select(AchievementRow.achievement_key).where(AchievementRow.user_id == user_id)
            )
            .scalars()
            .all()
        )

        # Insert new achievements (INSERT OR IGNORE for idempotency)
        newly_unlocked: list[str] = []
        for key in earned_keys:
            if key not in existing:
                stmt = sqlite_insert(AchievementRow).values(
                    user_id=user_id,
                    achievement_key=key,
                    unlocked_at=datetime.now(),
                )
                stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "achievement_key"])
                session.execute(stmt)
                newly_unlocked.append(key)

        if newly_unlocked:
            session.commit()

        return newly_unlocked


def grant_set_master(user_id: int, repo: Repository) -> bool:
    """Grant set_master achievement if not already earned.

    Called from set-completion endpoint when a set is 100%.
    Returns True if newly granted.
    """
    with Session(repo.engine) as session:
        stmt = sqlite_insert(AchievementRow).values(
            user_id=user_id,
            achievement_key="set_master",
            unlocked_at=datetime.now(),
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "achievement_key"])
        result = session.execute(stmt)
        session.commit()
        return (result.rowcount or 0) > 0


def get_user_achievements(user_id: int, repo: Repository) -> list[dict]:
    """Return all achievement definitions with user's unlock status."""
    with Session(repo.engine) as session:
        # Get user's unlocked achievements
        rows = session.execute(
            select(AchievementRow.achievement_key, AchievementRow.unlocked_at).where(
                AchievementRow.user_id == user_id
            )
        ).all()

        unlocked_map = {row.achievement_key: row.unlocked_at for row in rows}

        result = []
        for defn in ACHIEVEMENT_DEFINITIONS:
            unlocked_at = unlocked_map.get(defn["key"])
            result.append(
                {
                    "key": defn["key"],
                    "title_en": defn["title_en"],
                    "title_pt": defn["title_pt"],
                    "description_en": defn["description_en"],
                    "description_pt": defn["description_pt"],
                    "icon": defn["icon"],
                    "unlocked": unlocked_at is not None,
                    "unlocked_at": (unlocked_at.isoformat() if unlocked_at else None),
                }
            )

        return result

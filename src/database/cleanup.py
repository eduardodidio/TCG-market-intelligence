"""Cleanup logic to delete non-collection data from the database."""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.orm import Session

from src.database.backup import backup_database, extract_db_path
from src.database.models import (
    CardLegalityRow,
    CardRow,
    CollectionErrorRow,
    CreditBalanceRow,
    CreditTransactionRow,
    DeckCardRow,
    DeckRow,
    EvaluationEntryRow,
    LegalityHistoryRow,
    PortfolioSnapshotRow,
    PriceObservationRow,
    ScanRunRow,
    SourceCardRow,
    UserCollectionRow,
    UserRow,
)
from src.database.repository import Repository

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Clear prices by source
# ---------------------------------------------------------------------------

PROTECTED_SOURCES = {"liga", "manual"}


@dataclass
class ClearPricesResult:
    """Result of clearing price observations by source."""

    deleted: int = 0
    dry_run: bool = False
    backup_path: str | None = None


def clear_prices_by_source(
    db_url: str,
    source: str,
    *,
    dry_run: bool = True,
    skip_backup: bool = False,
) -> ClearPricesResult:
    """Delete all price_observations for a given source.

    Safety rules:
    - Refuses to delete protected sources (liga, manual).
    - Creates a backup before deleting (unless *skip_backup*).
    - Runs VACUUM after deletion to reclaim space.
    - Does NOT touch scan_runs (preserves audit trail).

    Parameters
    ----------
    db_url:
        SQLAlchemy database URL.
    source:
        The source value to match in price_observations.source.
    dry_run:
        If True, return the count without deleting.
    skip_backup:
        If True, skip the automatic pre-delete backup.

    Returns
    -------
    ClearPricesResult
        Count of rows deleted (or that would be deleted) and backup path.
    """
    if source in PROTECTED_SOURCES:
        raise ValueError(
            f"Refusing to clear protected source '{source}'. "
            f"Protected sources: {sorted(PROTECTED_SOURCES)}"
        )

    repo = Repository(db_url=db_url)

    with Session(repo.engine) as session:
        count = (
            session.execute(
                select(func.count())
                .select_from(PriceObservationRow)
                .where(PriceObservationRow.source == source)
            ).scalar()
            or 0
        )

    log.info("clear_prices.count", source=source, count=count, dry_run=dry_run)

    if dry_run:
        return ClearPricesResult(deleted=count, dry_run=True, backup_path=None)

    # Backup before deleting
    backup_path = None
    if not skip_backup:
        db_path = extract_db_path(db_url)
        backup_path = str(backup_database(db_path))

    # Delete
    with Session(repo.engine) as session:
        result = session.execute(
            delete(PriceObservationRow).where(PriceObservationRow.source == source)
        )
        deleted = result.rowcount
        session.commit()

    log.info("clear_prices.deleted", source=source, deleted=deleted)

    # VACUUM to reclaim space
    with repo.engine.connect() as conn:
        conn.execute(text("VACUUM"))
        conn.commit()
    log.info("clear_prices.vacuum_done")

    return ClearPricesResult(deleted=deleted, dry_run=False, backup_path=backup_path)


# ---------------------------------------------------------------------------
# Non-collection cleanup
# ---------------------------------------------------------------------------


@dataclass
class CleanupResult:
    """Counts of rows deleted (or that would be deleted in dry-run mode)."""

    cards_deleted: int = 0
    source_cards_deleted: int = 0
    observations_deleted: int = 0
    dry_run: bool = False
    backup_path: str | None = None


def _get_collection_identity_pairs(session: Session) -> set[tuple[str, str]]:
    """Return the set of (set_code, collector_number) from user_collection.

    All set_codes are already lowercase after normalization.
    """
    rows = session.execute(
        select(
            UserCollectionRow.set_code,
            UserCollectionRow.collector_number,
        )
    ).all()
    return {(r[0], r[1]) for r in rows}


def _find_cards_to_delete(session: Session, collection_pairs: set[tuple[str, str]]) -> list[int]:
    """Return card IDs that are NOT in the user's collection.

    All set_codes are already lowercase after normalization.
    """
    all_cards = session.execute(
        select(CardRow.id, CardRow.set_code, CardRow.collector_number)
    ).all()

    return [
        card_id
        for card_id, set_code, coll_num in all_cards
        if (set_code, coll_num) not in collection_pairs
    ]


def cleanup_non_collection_data(
    db_url: str,
    *,
    dry_run: bool = False,
    skip_backup: bool = False,
) -> CleanupResult:
    """Delete cards, source_cards, and price_observations not in the user's collection.

    Safety rules:
    - Refuses to run if user_collection is empty.
    - Creates a backup before deleting (unless *skip_backup* is True).
    - Uses a single transaction for atomicity.
    - Runs VACUUM after cleanup to reclaim space.

    Parameters
    ----------
    db_url:
        SQLAlchemy database URL (e.g. ``sqlite:///tcg_market.db``).
    dry_run:
        If True, compute and return counts without modifying data.
    skip_backup:
        If True, skip the automatic pre-delete backup.

    Returns
    -------
    CleanupResult
        Counts of rows deleted (or that would be deleted).
    """
    repo = Repository(db_url=db_url)
    result = CleanupResult(dry_run=dry_run)

    with Session(repo.engine) as session:
        # Safety check: refuse to clean if collection is empty
        collection_count = (
            session.execute(select(func.count()).select_from(UserCollectionRow)).scalar() or 0
        )

        if collection_count == 0:
            raise ValueError(
                "Cannot cleanup with empty collection. "
                "Import your collection first before running cleanup."
            )

        collection_pairs = _get_collection_identity_pairs(session)
        card_ids_to_delete = _find_cards_to_delete(session, collection_pairs)

        # Count what will be deleted
        # 1. Source cards + observations for cards being deleted
        source_card_ids_for_deleted: list[int] = []
        source_card_refs: list[tuple] = []
        if card_ids_to_delete:
            source_card_ids_for_deleted = list(
                session.execute(
                    select(SourceCardRow.id).where(SourceCardRow.card_id.in_(card_ids_to_delete))
                )
                .scalars()
                .all()
            )
            source_card_refs = list(
                session.execute(
                    select(SourceCardRow.source, SourceCardRow.external_id).where(
                        SourceCardRow.card_id.in_(card_ids_to_delete)
                    )
                ).all()
            )

        obs_count = 0
        for source, external_id in source_card_refs:
            count = (
                session.execute(
                    select(func.count())
                    .select_from(PriceObservationRow)
                    .where(
                        PriceObservationRow.source == source,
                        PriceObservationRow.external_id == external_id,
                    )
                ).scalar()
                or 0
            )
            obs_count += count

        # Also count orphan source_cards (card_id is NULL)
        orphan_source_cards = session.execute(
            select(SourceCardRow.id, SourceCardRow.source, SourceCardRow.external_id).where(
                SourceCardRow.card_id.is_(None)
            )
        ).all()

        orphan_obs_count = 0
        for _, source, external_id in orphan_source_cards:
            count = (
                session.execute(
                    select(func.count())
                    .select_from(PriceObservationRow)
                    .where(
                        PriceObservationRow.source == source,
                        PriceObservationRow.external_id == external_id,
                    )
                ).scalar()
                or 0
            )
            orphan_obs_count += count

        # Also count orphan price_observations whose (source, external_id) has no source_card
        all_source_card_refs = session.execute(
            select(SourceCardRow.source, SourceCardRow.external_id)
        ).all()
        known_refs = {(r[0], r[1]) for r in all_source_card_refs}

        all_obs_refs = session.execute(
            select(
                PriceObservationRow.source,
                PriceObservationRow.external_id,
                func.count(PriceObservationRow.id),
            ).group_by(PriceObservationRow.source, PriceObservationRow.external_id)
        ).all()
        fully_orphan_obs_count = sum(
            count for src, eid, count in all_obs_refs if (src, eid) not in known_refs
        )

        result.cards_deleted = len(card_ids_to_delete)
        result.source_cards_deleted = len(source_card_ids_for_deleted) + len(orphan_source_cards)
        result.observations_deleted = obs_count + orphan_obs_count + fully_orphan_obs_count

        # Nothing to do at all?
        if (
            result.cards_deleted == 0
            and result.source_cards_deleted == 0
            and result.observations_deleted == 0
        ):
            log.info("cleanup.nothing_to_clean", collection_size=collection_count)
            return result

        log.info(
            "cleanup.preview",
            cards=result.cards_deleted,
            source_cards=result.source_cards_deleted,
            observations=result.observations_deleted,
            dry_run=dry_run,
        )

        if dry_run:
            return result

    # -- Actual deletion (not dry-run) --

    # Backup before deleting
    backup_path = None
    if not skip_backup:
        db_path = extract_db_path(db_url)
        backup_path = backup_database(db_path)
        result.backup_path = str(backup_path)

    # Delete in a single transaction
    with Session(repo.engine) as session:
        # Re-fetch to ensure consistency
        collection_pairs = _get_collection_identity_pairs(session)
        card_ids_to_delete = _find_cards_to_delete(session, collection_pairs)

        # Get source_card refs for cards being deleted
        source_card_refs: list[tuple] = []
        if card_ids_to_delete:
            source_card_refs = list(
                session.execute(
                    select(SourceCardRow.source, SourceCardRow.external_id).where(
                        SourceCardRow.card_id.in_(card_ids_to_delete)
                    )
                ).all()
            )

        # Get orphan source_card refs
        orphan_refs = session.execute(
            select(SourceCardRow.source, SourceCardRow.external_id).where(
                SourceCardRow.card_id.is_(None)
            )
        ).all()

        all_refs_to_delete = list(source_card_refs) + list(orphan_refs)

        # 1. Delete price_observations for cards being removed + orphan source_cards
        obs_deleted = 0
        for source, external_id in all_refs_to_delete:
            r = session.execute(
                delete(PriceObservationRow).where(
                    PriceObservationRow.source == source,
                    PriceObservationRow.external_id == external_id,
                )
            )
            obs_deleted += r.rowcount

        # Delete fully orphan observations (no source_card at all)
        all_source_refs = session.execute(
            select(SourceCardRow.source, SourceCardRow.external_id)
        ).all()
        known = {(r[0], r[1]) for r in all_source_refs}
        obs_refs = session.execute(
            select(
                PriceObservationRow.source,
                PriceObservationRow.external_id,
            ).group_by(PriceObservationRow.source, PriceObservationRow.external_id)
        ).all()
        for src, eid in obs_refs:
            if (src, eid) not in known:
                r = session.execute(
                    delete(PriceObservationRow).where(
                        PriceObservationRow.source == src,
                        PriceObservationRow.external_id == eid,
                    )
                )
                obs_deleted += r.rowcount

        # 2. Delete source_cards for cards being removed + orphans
        sc_deleted = 0
        if card_ids_to_delete:
            sc_deleted += session.execute(
                delete(SourceCardRow).where(SourceCardRow.card_id.in_(card_ids_to_delete))
            ).rowcount
        sc_deleted += session.execute(
            delete(SourceCardRow).where(SourceCardRow.card_id.is_(None))
        ).rowcount

        # 3. Delete the cards themselves
        cards_deleted = 0
        if card_ids_to_delete:
            cards_deleted = session.execute(
                delete(CardRow).where(CardRow.id.in_(card_ids_to_delete))
            ).rowcount

        session.commit()

    # Update result with actual deletion counts
    result.cards_deleted = cards_deleted
    result.source_cards_deleted = sc_deleted
    result.observations_deleted = obs_deleted

    log.info(
        "cleanup.done",
        cards=cards_deleted,
        source_cards=sc_deleted,
        observations=obs_deleted,
    )

    # VACUUM to reclaim space (must run outside a transaction)
    with repo.engine.connect() as conn:
        conn.execute(text("VACUUM"))
        conn.commit()
    log.info("cleanup.vacuum_done")

    return result


# ---------------------------------------------------------------------------
# Full database reset (keep collection)
# ---------------------------------------------------------------------------


@dataclass
class ResetResult:
    """Counts of rows deleted (or that would be deleted in dry-run)."""

    prices_deleted: int = 0
    scan_runs_deleted: int = 0
    portfolio_snapshots_deleted: int = 0
    collection_errors_deleted: int = 0
    cards_deleted: int = 0
    source_cards_deleted: int = 0
    legalities_deleted: int = 0
    legality_history_deleted: int = 0
    cards_kept: int = 0
    dry_run: bool = False
    backup_path: str | None = None


def reset_database(
    db_url: str,
    *,
    dry_run: bool = True,
    skip_backup: bool = False,
) -> ResetResult:
    """Reset prices and remove non-collection cards from the database.

    Preserves user_collection, users, decks, credits, exchange_rates,
    scheduled_scans, and all other user-facing state.

    Safety rules:
    - Refuses to run if user_collection is empty.
    - Creates a backup before deleting (unless *skip_backup* is True).
    - Uses a single transaction for atomicity.
    - Runs VACUUM after cleanup to reclaim space.

    Parameters
    ----------
    db_url:
        SQLAlchemy database URL (e.g. ``sqlite:///tcg_market.db``).
    dry_run:
        If True, compute and return counts without modifying data.
    skip_backup:
        If True, skip the automatic pre-delete backup.

    Returns
    -------
    ResetResult
        Counts of rows deleted (or that would be deleted).
    """
    repo = Repository(db_url=db_url)

    with Session(repo.engine) as session:
        # Safety check: refuse if collection is empty
        collection_count = (
            session.execute(select(func.count()).select_from(UserCollectionRow)).scalar() or 0
        )
        if collection_count == 0:
            raise ValueError(
                "Cannot reset with empty collection. "
                "Import your collection first before running reset."
            )

        # Identify collection card_ids (cards that survive)
        collection_card_ids: set[int] = set(
            session.execute(
                select(UserCollectionRow.card_id).where(UserCollectionRow.card_id.is_not(None))
            )
            .scalars()
            .all()
        )

        # Count phase
        prices_count = (
            session.execute(select(func.count()).select_from(PriceObservationRow)).scalar() or 0
        )
        scan_runs_count = (
            session.execute(select(func.count()).select_from(ScanRunRow)).scalar() or 0
        )
        portfolio_count = (
            session.execute(select(func.count()).select_from(PortfolioSnapshotRow)).scalar() or 0
        )
        errors_count = (
            session.execute(select(func.count()).select_from(CollectionErrorRow)).scalar() or 0
        )

        # Cards to delete: all card IDs NOT in collection
        all_card_ids = set(session.execute(select(CardRow.id)).scalars().all())
        card_ids_to_delete = all_card_ids - collection_card_ids

        # Source cards to delete: card_id IS NULL OR card_id in cards-to-delete
        sc_null_count = (
            session.execute(
                select(func.count())
                .select_from(SourceCardRow)
                .where(SourceCardRow.card_id.is_(None))
            ).scalar()
            or 0
        )
        sc_delete_count = 0
        if card_ids_to_delete:
            sc_delete_count = (
                session.execute(
                    select(func.count())
                    .select_from(SourceCardRow)
                    .where(SourceCardRow.card_id.in_(card_ids_to_delete))
                ).scalar()
                or 0
            )

        # Legalities to delete
        legalities_count = 0
        legality_history_count = 0
        if card_ids_to_delete:
            legalities_count = (
                session.execute(
                    select(func.count())
                    .select_from(CardLegalityRow)
                    .where(CardLegalityRow.card_id.in_(card_ids_to_delete))
                ).scalar()
                or 0
            )
            legality_history_count = (
                session.execute(
                    select(func.count())
                    .select_from(LegalityHistoryRow)
                    .where(LegalityHistoryRow.card_id.in_(card_ids_to_delete))
                ).scalar()
                or 0
            )

    result = ResetResult(
        prices_deleted=prices_count,
        scan_runs_deleted=scan_runs_count,
        portfolio_snapshots_deleted=portfolio_count,
        collection_errors_deleted=errors_count,
        cards_deleted=len(card_ids_to_delete),
        source_cards_deleted=sc_null_count + sc_delete_count,
        legalities_deleted=legalities_count,
        legality_history_deleted=legality_history_count,
        cards_kept=len(collection_card_ids),
        dry_run=dry_run,
    )

    log.info(
        "reset.preview",
        prices=result.prices_deleted,
        scan_runs=result.scan_runs_deleted,
        portfolios=result.portfolio_snapshots_deleted,
        errors=result.collection_errors_deleted,
        cards=result.cards_deleted,
        source_cards=result.source_cards_deleted,
        legalities=result.legalities_deleted,
        legality_history=result.legality_history_deleted,
        cards_kept=result.cards_kept,
        dry_run=dry_run,
    )

    if dry_run:
        return result

    # Backup before deleting
    if not skip_backup:
        db_path = extract_db_path(db_url)
        backup_path = backup_database(db_path)
        result.backup_path = str(backup_path)

    # Delete phase (single transaction, order matters)
    with Session(repo.engine) as session:
        # a. price_observations (full truncate)
        session.execute(delete(PriceObservationRow))
        # b. scan_runs
        session.execute(delete(ScanRunRow))
        # c. portfolio_snapshots
        session.execute(delete(PortfolioSnapshotRow))
        # d. collection_errors
        session.execute(delete(CollectionErrorRow))

        if card_ids_to_delete:
            ids_list = list(card_ids_to_delete)
            # e. legality_history
            session.execute(
                delete(LegalityHistoryRow).where(LegalityHistoryRow.card_id.in_(ids_list))
            )
            # f. card_legalities
            session.execute(delete(CardLegalityRow).where(CardLegalityRow.card_id.in_(ids_list)))
            # g. source_cards (orphans + cards-to-delete)
            session.execute(
                delete(SourceCardRow).where(
                    SourceCardRow.card_id.is_(None) | SourceCardRow.card_id.in_(ids_list)
                )
            )
            # h. cards
            session.execute(delete(CardRow).where(CardRow.id.in_(ids_list)))
        else:
            # Still clean orphan source_cards even if no cards to delete
            session.execute(delete(SourceCardRow).where(SourceCardRow.card_id.is_(None)))

        session.commit()

    log.info(
        "reset.done",
        prices=result.prices_deleted,
        cards=result.cards_deleted,
        source_cards=result.source_cards_deleted,
    )

    # VACUUM to reclaim space (must run outside a transaction)
    with repo.engine.connect() as conn:
        conn.execute(text("VACUUM"))
        conn.commit()
    log.info("reset.vacuum_done")

    return result


# ---------------------------------------------------------------------------
# Orphan reference cleanup (pre-FK constraint preparation)
# ---------------------------------------------------------------------------


@dataclass
class OrphanCleanupResult:
    """Per-table counts of orphan records cleaned."""

    source_cards_unlinked: int = 0
    user_collection_unlinked: int = 0
    deck_cards_unlinked: int = 0
    card_legalities_deleted: int = 0
    legality_history_deleted: int = 0
    evaluation_entries_unlinked: int = 0
    deck_cards_no_deck_deleted: int = 0
    credit_balances_deleted: int = 0
    credit_transactions_deleted: int = 0
    dry_run: bool = False
    backup_path: str | None = None

    @property
    def total(self) -> int:
        return (
            self.source_cards_unlinked
            + self.user_collection_unlinked
            + self.deck_cards_unlinked
            + self.card_legalities_deleted
            + self.legality_history_deleted
            + self.evaluation_entries_unlinked
            + self.deck_cards_no_deck_deleted
            + self.credit_balances_deleted
            + self.credit_transactions_deleted
        )


def _count_orphans_card_id(session: Session, model_class, label: str) -> int:
    """Count rows where card_id references a non-existent cards.id."""
    stmt = (
        select(func.count())
        .select_from(model_class)
        .where(
            model_class.card_id.is_not(None),
            ~model_class.card_id.in_(select(CardRow.id)),
        )
    )
    return session.execute(stmt).scalar() or 0


def cleanup_orphan_references(
    db_url: str,
    *,
    dry_run: bool = True,
    skip_backup: bool = False,
) -> OrphanCleanupResult:
    """Clean orphan references that would violate FK constraints.

    For card_id references:
    - source_cards, user_collection, deck_cards, evaluation_entries: SET NULL
    - card_legalities, legality_history: DELETE

    For other FK references:
    - deck_cards with invalid deck_id: DELETE
    - credit_balances, credit_transactions with invalid user_id: DELETE

    Parameters
    ----------
    db_url:
        SQLAlchemy database URL.
    dry_run:
        If True, return counts without modifying data.
    skip_backup:
        If True, skip the automatic pre-delete backup.

    Returns
    -------
    OrphanCleanupResult
        Per-table counts of orphan records cleaned.
    """
    repo = Repository(db_url=db_url)
    result = OrphanCleanupResult(dry_run=dry_run)

    with Session(repo.engine) as session:
        # Count orphans in each table
        valid_card_ids = select(CardRow.id)

        # 1-3: card_id -> cards.id (SET NULL targets)
        result.source_cards_unlinked = _count_orphans_card_id(
            session, SourceCardRow, "source_cards"
        )
        result.user_collection_unlinked = _count_orphans_card_id(
            session, UserCollectionRow, "user_collection"
        )
        result.deck_cards_unlinked = _count_orphans_card_id(session, DeckCardRow, "deck_cards")

        # 4-5: card_id -> cards.id (DELETE targets)
        result.card_legalities_deleted = _count_orphans_card_id(
            session, CardLegalityRow, "card_legalities"
        )
        result.legality_history_deleted = _count_orphans_card_id(
            session, LegalityHistoryRow, "legality_history"
        )

        # 6: evaluation_entries.card_id -> cards.id (SET NULL)
        result.evaluation_entries_unlinked = _count_orphans_card_id(
            session, EvaluationEntryRow, "evaluation_entries"
        )

        # 7: deck_cards.deck_id -> decks.id (DELETE)
        result.deck_cards_no_deck_deleted = (
            session.execute(
                select(func.count())
                .select_from(DeckCardRow)
                .where(~DeckCardRow.deck_id.in_(select(DeckRow.id)))
            ).scalar()
            or 0
        )

        # 8: credit_balances.user_id -> users.id (DELETE)
        result.credit_balances_deleted = (
            session.execute(
                select(func.count())
                .select_from(CreditBalanceRow)
                .where(~CreditBalanceRow.user_id.in_(select(UserRow.id)))
            ).scalar()
            or 0
        )

        # 9: credit_transactions.user_id -> users.id (DELETE)
        result.credit_transactions_deleted = (
            session.execute(
                select(func.count())
                .select_from(CreditTransactionRow)
                .where(~CreditTransactionRow.user_id.in_(select(UserRow.id)))
            ).scalar()
            or 0
        )

    log.info(
        "orphan_cleanup.preview",
        source_cards=result.source_cards_unlinked,
        user_collection=result.user_collection_unlinked,
        deck_cards=result.deck_cards_unlinked,
        card_legalities=result.card_legalities_deleted,
        legality_history=result.legality_history_deleted,
        evaluation_entries=result.evaluation_entries_unlinked,
        deck_cards_no_deck=result.deck_cards_no_deck_deleted,
        credit_balances=result.credit_balances_deleted,
        credit_transactions=result.credit_transactions_deleted,
        total=result.total,
        dry_run=dry_run,
    )

    if dry_run:
        return result

    # Backup before mutations
    if not skip_backup:
        db_path = extract_db_path(db_url)
        backup_path = backup_database(db_path)
        result.backup_path = str(backup_path)

    # Execute cleanup in a single transaction
    with Session(repo.engine) as session:
        valid_card_ids = select(CardRow.id)

        # SET NULL for card_id orphans
        for model_class in (SourceCardRow, UserCollectionRow, DeckCardRow, EvaluationEntryRow):
            session.execute(
                update(model_class)
                .where(
                    model_class.card_id.is_not(None),
                    ~model_class.card_id.in_(valid_card_ids),
                )
                .values(card_id=None)
            )

        # DELETE for card_id orphans (legalities)
        for model_class in (CardLegalityRow, LegalityHistoryRow):
            session.execute(
                delete(model_class).where(
                    ~model_class.card_id.in_(valid_card_ids),
                )
            )

        # DELETE deck_cards with invalid deck_id
        session.execute(delete(DeckCardRow).where(~DeckCardRow.deck_id.in_(select(DeckRow.id))))

        # DELETE credit rows with invalid user_id
        session.execute(
            delete(CreditBalanceRow).where(~CreditBalanceRow.user_id.in_(select(UserRow.id)))
        )
        session.execute(
            delete(CreditTransactionRow).where(
                ~CreditTransactionRow.user_id.in_(select(UserRow.id))
            )
        )

        session.commit()

    log.info("orphan_cleanup.done", total=result.total)
    return result

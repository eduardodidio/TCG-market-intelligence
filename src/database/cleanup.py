"""Cleanup logic to delete non-collection data from the database."""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from src.database.backup import backup_database, extract_db_path
from src.database.models import (
    CardRow,
    PriceObservationRow,
    SourceCardRow,
    UserCollectionRow,
)
from src.database.repository import Repository

log = structlog.get_logger()


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

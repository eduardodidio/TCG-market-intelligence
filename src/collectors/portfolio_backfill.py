"""Portfolio backfill — acquisition prices and synthetic historical snapshots.

Backfills acquisition_price for collection entries missing them, and
generates synthetic portfolio snapshots by replaying the user's collection
state and price observations day-by-day over a configurable window.
"""

from __future__ import annotations

from bisect import bisect_right
from datetime import date, datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from src.collection.converter import is_foil_entry
from src.database.models import (
    PortfolioSnapshotRow,
    PriceObservationRow,
    SourceCardRow,
    UserCollectionRow,
)
from src.database.repository import Repository

log = structlog.get_logger()


# ── Acquisition price backfill ───────────────────────────────────


def _pick_price(obs: PriceObservationRow) -> Decimal | None:
    """Return the best available price from an observation row.

    Priority: median_price > tcg_price > last_sold_price.
    """
    if obs.median_price is not None:
        return obs.median_price
    if obs.tcg_price is not None:
        return obs.tcg_price
    if obs.last_sold_price is not None:
        return obs.last_sold_price
    return None


def _find_nearest_observation(
    session: Session,
    card_id: int,
    target_dt: datetime,
    is_foil: bool = False,
) -> PriceObservationRow | None:
    """Find the price observation closest to *target_dt* for a card.

    Prefers observations on or before the target date.  If none exist
    before, falls back to the earliest observation after.

    Searches multiple external_id patterns to match how
    ``get_latest_prices_batch`` resolves prices:
    1. source_cards linked to this card_id (catalog entries)
    2. ``liga_{card_id}`` direct pattern (Liga scan convention)
    3. ``liga_{card_id}_foil`` direct pattern (foil Liga prices)
    4. ``manual_{card_id}`` direct pattern (manual price entries)
    """
    target_date = target_dt.date() if isinstance(target_dt, datetime) else target_dt

    # Collect all (source, external_id) pairs to search
    search_pairs: list[tuple[str, str]] = []

    # 1. From source_cards table
    source_cards_stmt = select(SourceCardRow).where(SourceCardRow.card_id == card_id)
    for sc in session.execute(source_cards_stmt).scalars().all():
        search_pairs.append((sc.source, sc.external_id))

    # 2. Direct Liga pattern: liga_{card_id}
    search_pairs.append(("liga", f"liga_{card_id}"))

    # 2b. Foil-specific Liga pattern: liga_{card_id}_foil
    if is_foil:
        # Insert foil pattern before normal liga so it is checked first
        search_pairs.insert(-1, ("liga", f"liga_{card_id}_foil"))

    # 3. Direct manual pattern: manual_{card_id}
    search_pairs.append(("manual", f"manual_{card_id}"))

    best_obs: PriceObservationRow | None = None
    best_diff: int | None = None

    for source, external_id in search_pairs:
        before_stmt = (
            select(PriceObservationRow)
            .where(
                and_(
                    PriceObservationRow.source == source,
                    PriceObservationRow.external_id == external_id,
                    PriceObservationRow.observed_at <= target_date,
                )
            )
            .order_by(PriceObservationRow.observed_at.desc())
            .limit(1)
        )
        obs = session.execute(before_stmt).scalar_one_or_none()

        if obs is None:
            after_stmt = (
                select(PriceObservationRow)
                .where(
                    and_(
                        PriceObservationRow.source == source,
                        PriceObservationRow.external_id == external_id,
                        PriceObservationRow.observed_at > target_date,
                    )
                )
                .order_by(PriceObservationRow.observed_at.asc())
                .limit(1)
            )
            obs = session.execute(after_stmt).scalar_one_or_none()

        if obs is not None:
            diff = abs((obs.observed_at - target_date).days)
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_obs = obs

    return best_obs


def backfill_acquisition_prices(
    repo: Repository,
    user_id: str | None = None,
) -> dict:
    """Backfill acquisition_price for collection entries that lack one.

    Args:
        repo: Repository instance (must have ``self.engine``).
        user_id: Optional filter — only backfill this user's entries.

    Returns:
        Summary dict ``{"updated": N, "skipped": N, "total": N}``.
    """
    updated = 0
    skipped = 0

    with Session(repo.engine) as session:
        stmt = select(UserCollectionRow).where(UserCollectionRow.acquisition_price.is_(None))
        if user_id is not None:
            stmt = stmt.where(UserCollectionRow.user_id == user_id)

        entries = session.execute(stmt).scalars().all()
        total = len(entries)

        log.info(
            "portfolio_backfill_start",
            total_entries=total,
            user_id=user_id,
        )

        for entry in entries:
            if entry.card_id is None:
                log.warning(
                    "portfolio_backfill_no_card_id",
                    entry_id=entry.id,
                    user_id=entry.user_id,
                )
                skipped += 1
                continue

            obs = _find_nearest_observation(
                session,
                entry.card_id,
                entry.created_at,
                is_foil=is_foil_entry(entry.extras),
            )
            if obs is None:
                log.warning(
                    "portfolio_backfill_no_price",
                    entry_id=entry.id,
                    card_id=entry.card_id,
                    user_id=entry.user_id,
                )
                skipped += 1
                continue

            price = _pick_price(obs)
            if price is None:
                log.warning(
                    "portfolio_backfill_all_prices_null",
                    entry_id=entry.id,
                    card_id=entry.card_id,
                    observation_id=obs.id,
                )
                skipped += 1
                continue

            entry.acquisition_price = price
            entry.acquired_at = obs.observed_at
            updated += 1

            log.debug(
                "portfolio_backfill_updated",
                entry_id=entry.id,
                card_id=entry.card_id,
                price=str(price),
                observed_at=str(obs.observed_at),
            )

        session.commit()

    log.info(
        "portfolio_backfill_done",
        updated=updated,
        skipped=skipped,
        total=total,
    )

    return {"updated": updated, "skipped": skipped, "total": total}


# ── Portfolio snapshot backfill ──────────────────────────────────


def backfill_portfolio_snapshots(
    repo: Repository,
    user_id: str,
    days: int = 30,
) -> dict:
    """Generate synthetic portfolio snapshots for the past *days* days.

    For each date in ``[today - days, today]``, the function reconstructs the
    user's collection value by finding the latest price observation on or
    before that date for each card the user owned at that point.

    Dates that already have a snapshot are skipped to avoid overwriting real
    data produced by :func:`take_snapshot`.

    Returns ``{"days_filled": N, "days_skipped": N}``.
    """
    today = date.today()
    start_date = today - timedelta(days=days)

    log.info(
        "portfolio_snapshot_backfill_start",
        user_id=user_id,
        start_date=str(start_date),
        end_date=str(today),
        days=days,
    )

    with Session(repo.engine) as session:
        existing_snapshot_dates = _load_existing_snapshot_dates(session, user_id, start_date, today)

        collection_entries = _load_collection_entries(session, user_id)
        if not collection_entries:
            log.info("portfolio_snapshot_backfill_no_collection", user_id=user_id)
            return {"days_filled": 0, "days_skipped": 0}

        card_ids = {e.card_id for e in collection_entries if e.card_id is not None}
        foil_card_ids = {
            e.card_id
            for e in collection_entries
            if e.card_id is not None and is_foil_entry(e.extras)
        }
        card_external_ids = _load_card_external_ids(session, card_ids, foil_card_ids)

        all_external_ids: set[str] = set()
        for ext_ids in card_external_ids.values():
            all_external_ids.update(ext_ids)
        price_index = _build_price_index(session, all_external_ids)

    days_filled = 0
    days_skipped = 0

    current = start_date
    while current <= today:
        if current in existing_snapshot_dates:
            days_skipped += 1
            current += timedelta(days=1)
            continue

        total_value = Decimal("0")
        priced_count = 0
        total_count = 0

        for entry in collection_entries:
            entry_created = (
                entry.created_at.date() if hasattr(entry.created_at, "date") else entry.created_at
            )
            if entry_created > current:
                continue
            if entry.card_id is None:
                total_count += entry.quantity
                continue

            total_count += entry.quantity
            ext_ids = card_external_ids.get(entry.card_id, [])

            best_price = _find_best_price(price_index, ext_ids, current)
            if best_price is not None:
                total_value += best_price * entry.quantity
                priced_count += 1

        repo.upsert_portfolio_snapshot(
            user_id=user_id,
            snapshot_date=current,
            total_value_brl=total_value,
            priced_card_count=priced_count,
            total_card_count=total_count,
        )
        days_filled += 1
        current += timedelta(days=1)

    log.info(
        "portfolio_snapshot_backfill_complete",
        user_id=user_id,
        days_filled=days_filled,
        days_skipped=days_skipped,
    )
    return {"days_filled": days_filled, "days_skipped": days_skipped}


# ── Snapshot backfill helpers ────────────────────────────────────


def _load_existing_snapshot_dates(
    session: Session,
    user_id: str,
    start_date: date,
    end_date: date,
) -> set[date]:
    """Return the set of dates that already have a portfolio snapshot."""
    stmt = select(PortfolioSnapshotRow.snapshot_date).where(
        PortfolioSnapshotRow.user_id == user_id,
        PortfolioSnapshotRow.snapshot_date >= start_date,
        PortfolioSnapshotRow.snapshot_date <= end_date,
    )
    rows = session.execute(stmt).scalars().all()
    return set(rows)


def _load_collection_entries(
    session: Session,
    user_id: str,
) -> list[UserCollectionRow]:
    """Load all collection entries for a user."""
    stmt = select(UserCollectionRow).where(UserCollectionRow.user_id == user_id)
    return list(session.execute(stmt).scalars().all())


def _load_card_external_ids(
    session: Session,
    card_ids: set[int],
    foil_card_ids: set[int] | None = None,
) -> dict[int, list[str]]:
    """Map card_id -> list of external_ids from source_cards + direct patterns.

    Includes both source_cards entries and the direct Liga/manual patterns
    (``liga_{card_id}``, ``manual_{card_id}``) to match the lookup logic
    in ``get_latest_prices_batch``.

    For cards in *foil_card_ids*, also adds ``liga_{card_id}_foil`` so that
    foil-specific Liga prices are included in backfill calculations.
    """
    if not card_ids:
        return {}
    _foil_ids = foil_card_ids or set()
    stmt = select(SourceCardRow.card_id, SourceCardRow.external_id).where(
        SourceCardRow.card_id.in_(list(card_ids))
    )
    rows = session.execute(stmt).all()
    result: dict[int, list[str]] = {}
    for card_id, external_id in rows:
        result.setdefault(card_id, []).append(external_id)

    # Add direct Liga and manual patterns for all card_ids
    for card_id in card_ids:
        ext_list = result.setdefault(card_id, [])
        liga_ext = f"liga_{card_id}"
        manual_ext = f"manual_{card_id}"
        if liga_ext not in ext_list:
            ext_list.append(liga_ext)
        if manual_ext not in ext_list:
            ext_list.append(manual_ext)
        # Add foil-specific Liga pattern for foil entries.
        # Placed first so _find_best_price prefers foil when dates match.
        if card_id in _foil_ids:
            liga_foil_ext = f"liga_{card_id}_foil"
            if liga_foil_ext not in ext_list:
                ext_list.insert(0, liga_foil_ext)

    return result


def _build_price_index(
    session: Session,
    external_ids: set[str],
) -> dict[str, tuple[list[date], list[Decimal]]]:
    """Build a sorted price index for fast date lookups.

    Returns ``{external_id: (sorted_dates, corresponding_prices)}``.
    For each external_id, only the best price per day is kept (preferring
    median_price, falling back to tcg_price or last_sold_price).
    """
    if not external_ids:
        return {}

    stmt = (
        select(
            PriceObservationRow.external_id,
            PriceObservationRow.observed_at,
            PriceObservationRow.median_price,
            PriceObservationRow.tcg_price,
            PriceObservationRow.last_sold_price,
        )
        .where(PriceObservationRow.external_id.in_(list(external_ids)))
        .order_by(PriceObservationRow.external_id, PriceObservationRow.observed_at)
    )
    rows = session.execute(stmt).all()

    raw: dict[str, dict[date, Decimal]] = {}
    for ext_id, obs_date, median, tcg, last_sold in rows:
        price = median or tcg or last_sold
        if price is None:
            continue
        day_map = raw.setdefault(ext_id, {})
        day_map[obs_date] = Decimal(str(price))

    index: dict[str, tuple[list[date], list[Decimal]]] = {}
    for ext_id, day_map in raw.items():
        sorted_dates = sorted(day_map.keys())
        sorted_prices = [day_map[d] for d in sorted_dates]
        index[ext_id] = (sorted_dates, sorted_prices)

    return index


def _find_best_price(
    price_index: dict[str, tuple[list[date], list[Decimal]]],
    external_ids: list[str],
    target_date: date,
) -> Decimal | None:
    """Find the most recent price on or before *target_date* for any of the external_ids.

    Uses binary search for efficiency.  When multiple external_ids have a
    price, the one with the most recent observation wins.
    """
    best_price: Decimal | None = None
    best_date: date | None = None

    for ext_id in external_ids:
        entry = price_index.get(ext_id)
        if entry is None:
            continue
        dates, prices = entry
        idx = bisect_right(dates, target_date) - 1
        if idx < 0:
            continue
        obs_date = dates[idx]
        if best_date is None or obs_date > best_date:
            best_date = obs_date
            best_price = prices[idx]

    return best_price

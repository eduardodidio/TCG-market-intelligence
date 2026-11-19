"""Backfill acquisition prices from a DeckCheck Binder CSV into user_collection.

Only updates `acquisition_price` (and optionally `acquired_at`) on existing
collection entries. Never creates, deletes, or modifies the collection itself.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.repository import Repository


@dataclass
class BackfillResult:
    """Summary of a price backfill run."""

    total_csv_rows: int = 0
    matched: int = 0
    skipped_has_price: int = 0
    not_found: int = 0
    applied: int = 0
    errors: list[str] = field(default_factory=list)
    exchange_rate: Decimal | None = None


def _parse_price(raw: str) -> Decimal | None:
    """Parse a price string like '0.19' or '12.50' to Decimal, or None."""
    raw = raw.strip()
    if not raw or raw == "0" or raw == "0.00":
        return None
    try:
        return Decimal(raw)
    except Exception:
        return None


def _normalize_key(name: str, set_code: str, collector_number: str) -> tuple[str, str, str]:
    return (name.strip().lower(), set_code.strip().lower(), collector_number.strip().lower())


def backfill_from_deckcheck_csv(
    csv_path: str | Path,
    repo: "Repository",
    user_id: str,
    currency: str = "USD",
    exchange_rate: Decimal | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> BackfillResult:
    """Import acquisition prices from a DeckCheck Binder CSV.

    Parameters
    ----------
    csv_path:
        Path to the DeckCheck CSV export.
    repo:
        Database repository.
    user_id:
        Target user whose collection entries will be updated.
    currency:
        Currency of the ``Purchase Price`` column (``USD`` or ``BRL``).
    exchange_rate:
        USD->BRL conversion rate. Required when ``currency == "USD"``.
        Ignored when ``currency == "BRL"``.
    overwrite:
        If True, overwrite entries that already have an acquisition_price.
    dry_run:
        If True, compute counts but do not write anything.

    Returns
    -------
    BackfillResult with counts and optional error messages.
    """
    result = BackfillResult(exchange_rate=exchange_rate)
    csv_path = Path(csv_path)

    # --- 1. Read CSV rows ------------------------------------------------
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        csv_rows = list(reader)
    result.total_csv_rows = len(csv_rows)

    # --- 2. Load all collection entries for user -------------------------
    # Paginate to get everything (limit=9999)
    entries = repo.list_collection(user_id, sort_by="name", limit=9999)

    # Build lookup: (name_en_lower, set_code_lower, collector_number_lower) -> entry
    by_full_key: dict[tuple[str, str, str], list] = {}
    by_set_num: dict[tuple[str, str], list] = {}
    for entry in entries:
        name = (entry.name_en or "").strip().lower()
        sc = (entry.set_code or "").strip().lower()
        cn = (entry.collector_number or "").strip().lower()
        full_key = (name, sc, cn)
        by_full_key.setdefault(full_key, []).append(entry)
        set_num_key = (sc, cn)
        by_set_num.setdefault(set_num_key, []).append(entry)

    # --- 3. Match CSV rows to collection entries -------------------------
    updates: list[tuple[int, Decimal]] = []  # (entry_id, price_brl)

    for row in csv_rows:
        name = row.get("Name", "").strip()
        set_code = row.get("Set Code", "").strip()
        collector_number = row.get("Collector Number", "").strip()
        price_str = row.get("Purchase Price", "").strip()

        price = _parse_price(price_str)
        if price is None:
            result.not_found += 1
            continue

        # Convert to BRL
        price_brl = _convert_price(price, currency, exchange_rate)
        if price_brl is None:
            result.errors.append(
                f"Cannot convert price for '{name}' ({set_code} #{collector_number}): "
                f"currency={currency}, rate={exchange_rate}"
            )
            result.not_found += 1
            continue

        # Try full match first
        full_key = _normalize_key(name, set_code, collector_number)
        matched_entries = by_full_key.get(full_key)

        # Fallback: match by (set_code, collector_number) only
        if not matched_entries:
            set_num_key = (full_key[1], full_key[2])
            matched_entries = by_set_num.get(set_num_key)

        if not matched_entries:
            result.not_found += 1
            continue

        result.matched += 1

        # Update all matching entries (could be multiple quantities)
        for entry in matched_entries:
            if entry.acquisition_price is not None and not overwrite:
                result.skipped_has_price += 1
                continue
            updates.append((entry.id, price_brl))

    # --- 4. Apply updates ------------------------------------------------
    if not dry_run and updates:
        with repo.transaction() as session:
            for entry_id, price_brl in updates:
                repo.update_collection_entry(
                    entry_id,
                    user_id,
                    {"acquisition_price": price_brl},
                    session=session,
                )
    result.applied = len(updates) if not dry_run else 0

    return result


def _convert_price(
    price: Decimal,
    currency: str,
    exchange_rate: Decimal | None,
) -> Decimal | None:
    """Convert price to BRL. Returns None if conversion is impossible."""
    curr = currency.upper().strip()
    if curr == "BRL":
        return price
    if curr == "USD":
        if exchange_rate is None or exchange_rate <= 0:
            return None
        return (price * exchange_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return None

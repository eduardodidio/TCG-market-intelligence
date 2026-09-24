"""Import user card collection from CSV export."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.collection.csv_columns import ColumnMap, detect_file_currency, resolve_columns
from src.currency.import_conversion import RateLookup, to_brl
from src.currency.money import detect_symbol, parse_money
from src.currency.types import CurrencyChoice, SupportedCurrency
from src.database.models import Base, CardRow, UserCollectionRow
from src.utils.set_code_map import map_to_scryfall_set_code

_MAX_WARNINGS = 20


def _detect_encoding(file_path: Path) -> str:
    """Try UTF-8 first (with BOM), fall back to cp1252 for Liga exports."""
    raw = file_path.read_bytes()
    try:
        raw.decode("utf-8-sig")
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "cp1252"


def _field(row: dict[str, str], cmap: ColumnMap, canonical: str) -> str | None:
    header = cmap.fields.get(canonical)
    if header is None:
        return None
    return row.get(header)


def _parse_quantity(raw: str | None) -> int | None:
    """Tolerate "2", "" (-> 1), "2.0". Invalid values return None (row skipped)."""
    raw = (raw or "").strip()
    if not raw:
        return 1
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return int(float(raw))
    except ValueError:
        return None


def _resolve_extras(extras_header: str | None, raw_value: str | None) -> str | None:
    value = (raw_value or "").strip()
    if not extras_header or not value:
        return None
    if extras_header.strip().lower() == "foil":
        lowered = value.lower()
        if lowered in ("foil", "true"):
            return "Foil"
        if lowered == "etched":
            return "Etched"
        return None
    return value


def _row_currency(
    raw_price: str | None,
    currency_header_value: str | None,
    choice: CurrencyChoice,
    default_currency: SupportedCurrency,
) -> str:
    """Decide the currency for one row (may be an unsupported code like "EUR")."""
    if choice in ("BRL", "USD"):
        return choice

    if currency_header_value:
        cell = currency_header_value.strip().upper()
        if cell in ("BRL", "USD"):
            return cell
        sym = detect_symbol(currency_header_value)
        if sym:
            return sym

    sym = detect_symbol(raw_price or "")
    if sym:
        return sym

    return default_currency


def import_collection_csv(
    engine,
    csv_path: str | Path,
    user_id: str,
    *,
    currency: CurrencyChoice = "auto",
    rate_lookup: RateLookup | None = None,
    dry_run: bool = False,
    today: date | None = None,
) -> dict:
    """Parse a collection CSV and insert rows into user_collection.

    Prices (when present) are converted to BRL at import time; BRL is the
    only currency ever stored in ``acquisition_price``.

    Returns summary dict with counts, currency detection, and (unless
    ``dry_run``) the list of new entry IDs.
    """
    csv_path = Path(csv_path)
    today = today or date.today()
    on_rate_missing: RateLookup = rate_lookup or (lambda _d: None)

    imported = 0
    skipped = 0
    linked = 0
    priced = 0
    converted = 0
    exchange_rate: str | None = None
    all_warnings: list[str] = []
    new_entry_ids: list[int] = []

    encoding = _detect_encoding(csv_path)

    with open(csv_path, encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        raw_rows = list(reader)

    cmap = resolve_columns(headers)
    detection = detect_file_currency(cmap, raw_rows, currency)
    price_header = cmap.fields.get("price")
    currency_header = cmap.fields.get("currency")
    extras_header = cmap.fields.get("extras")

    rows_to_insert: list[dict] = []

    for line_number, row in enumerate(raw_rows, start=2):
        set_code = (_field(row, cmap, "set_code") or "").strip().lower()
        set_code = map_to_scryfall_set_code(set_code)
        collector_number = (_field(row, cmap, "collector_number") or "").strip()
        if not set_code or not collector_number:
            skipped += 1
            continue

        quantity = _parse_quantity(_field(row, cmap, "quantity"))
        if quantity is None:
            skipped += 1
            continue

        name_en = (_field(row, cmap, "name_en") or "").strip() or None
        name_pt = (_field(row, cmap, "name_pt") or "").strip() or None
        set_name_en = (_field(row, cmap, "set_name_en") or "").strip() or None
        quality = (_field(row, cmap, "quality") or "").strip() or None
        language = (_field(row, cmap, "language") or "").strip() or None
        rarity = (_field(row, cmap, "rarity") or "").strip() or None
        color = (_field(row, cmap, "color") or "").strip() or None
        extras = _resolve_extras(extras_header, _field(row, cmap, "extras"))
        set_name_pt = (_field(row, cmap, "set_name_pt") or "").strip() or None
        notes = (_field(row, cmap, "notes") or "").strip() or None

        acquisition_price = None

        if price_header:
            raw_price = (row.get(price_header) or "").strip()
            if raw_price:
                row_currency = _row_currency(
                    raw_price, row.get(currency_header) if currency_header else None,
                    currency, detection.currency,
                )
                money_hint: SupportedCurrency | None = (
                    row_currency if row_currency in ("BRL", "USD") else None
                )
                amount, _symbol = parse_money(raw_price, hint=money_hint)
                if amount is None:
                    all_warnings.append(f"row {line_number}: invalid_price")
                else:
                    conv = to_brl(amount, row_currency, today, on_rate_missing)
                    if conv.brl is not None:
                        acquisition_price = conv.brl
                        priced += 1
                        if conv.rate is not None:
                            converted += 1
                            exchange_rate = str(conv.rate)
                    if conv.warning:
                        all_warnings.append(f"row {line_number}: {conv.warning}")

        rows_to_insert.append(
            {
                "user_id": user_id,
                "set_code": set_code,
                "collector_number": collector_number,
                "name_en": name_en,
                "name_pt": name_pt,
                "set_name_en": set_name_en,
                "quantity": quantity,
                "quality": quality,
                "language": language,
                "rarity": rarity,
                "color": color,
                "extras": extras,
                "set_name_pt": set_name_pt,
                "notes": notes,
                "acquisition_price": acquisition_price,
            }
        )

    if len(all_warnings) > _MAX_WARNINGS:
        price_warnings = all_warnings[:_MAX_WARNINGS]
        price_warnings.append(f"... and {len(all_warnings) - _MAX_WARNINGS} more")
    else:
        price_warnings = all_warnings

    if dry_run:
        return {
            "imported": len(rows_to_insert),
            "skipped": skipped,
            "linked": 0,
            "total_csv_rows": len(rows_to_insert) + skipped,
            "new_entry_ids": [],
            "detected_currency": detection.currency,
            "currency_source": detection.source,
            "currency_confidence": detection.confidence,
            "currency_evidence": detection.evidence,
            "priced": priced,
            "converted": converted,
            "exchange_rate": exchange_rate,
            "price_warnings": price_warnings,
            "dry_run": True,
        }

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        try:
            # Clear existing collection for this user before re-import
            session.query(UserCollectionRow).filter(UserCollectionRow.user_id == user_id).delete()

            for data in rows_to_insert:
                # Link to canonical card (both sides are lowercase after normalization)
                card = session.execute(
                    select(CardRow).where(
                        CardRow.game == "magic",
                        CardRow.set_code == data["set_code"],
                        CardRow.collector_number == data["collector_number"],
                    )
                ).scalar_one_or_none()

                if card:
                    card_id = card.id
                else:
                    # Auto-canonize: create canonical card from collection data
                    new_card = CardRow(
                        game="magic",
                        name_en=data["name_en"],
                        name_pt=data["name_pt"],
                        set_code=data["set_code"],
                        collector_number=data["collector_number"],
                    )
                    session.add(new_card)
                    session.flush()
                    card_id = new_card.id

                linked += 1

                row = UserCollectionRow(card_id=card_id, **data)
                session.add(row)
                session.flush()  # populate row.id
                new_entry_ids.append(row.id)
                imported += 1

            session.commit()
        except Exception:
            session.rollback()
            raise

    return {
        "imported": imported,
        "skipped": skipped,
        "linked": linked,
        "total_csv_rows": imported + skipped,
        "new_entry_ids": new_entry_ids,
        "detected_currency": detection.currency,
        "currency_source": detection.source,
        "currency_confidence": detection.confidence,
        "currency_evidence": detection.evidence,
        "priced": priced,
        "converted": converted,
        "exchange_rate": exchange_rate,
        "price_warnings": price_warnings,
        "dry_run": False,
    }

"""Purchase HTML import endpoints.

Allows users to upload saved HTML files from Nerdz Cards and Liga Magic
purchase history, preview matched cards, and bulk-apply acquisition prices
to their collection.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import structlog
from fastapi import APIRouter, Depends, Query, UploadFile
from fastapi.exceptions import HTTPException

from src.api.deps import get_current_user, get_db
from src.database.models import UserCollectionRow
from src.database.repository import Repository
from src.services.purchase_matcher import match_purchases
from src.services.purchase_parser import parse_purchase_html

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/purchases", tags=["purchases"])

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/import-preview")
async def import_preview(
    files: list[UploadFile],
    overwrite_existing: bool = Query(False),
    user=Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Upload HTML files, parse, match to collection, return preview."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # Validate files
    valid_files: list[tuple[str, str]] = []
    for f in files:
        fname = f.filename or "unknown.html"
        if not fname.lower().endswith((".html", ".htm")):
            raise HTTPException(
                status_code=400,
                detail=f"File '{fname}' is not an HTML file",
            )
        content_bytes = await f.read()
        if len(content_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File '{fname}' exceeds 5MB limit",
            )
        # Try UTF-8 first, fall back to latin-1
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = content_bytes.decode("latin-1")
        valid_files.append((fname, content))

    # Parse all files
    all_parsed_items = []
    all_orders = []
    all_warnings: list[str] = []
    sealed_count = 0

    for fname, content in valid_files:
        try:
            orders = parse_purchase_html(content, fname)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        for order in orders:
            all_orders.append(order)
            all_parsed_items.extend(order.items)

    # Load user collection
    user_id = str(user.id)
    collection = _load_full_collection(repo, user_id)

    # Match
    report = match_purchases(all_parsed_items, collection)
    all_warnings.extend(report.warnings)

    # Build response
    matches = []
    for r in report.matched:
        if not overwrite_existing and r.already_has_price:
            continue
        item = r.parsed_item
        match_id = f"match_{r.collection_entry_id}_{item.order_number}"
        matches.append(
            {
                "id": match_id,
                "card_name_parsed": _format_parsed_name(item),
                "card_name_collection": r.collection_entry_name,
                "set_code_parsed": item.set_code,
                "set_code_collection": r.collection_set_code,
                "collector_number": item.collector_number,
                "quantity_parsed": item.quantity,
                "quantity_collection": r.collection_quantity,
                "unit_price": str(item.unit_price),
                "order_date": item.order_date.isoformat() if item.order_date else None,
                "order_number": item.order_number,
                "store_name": item.store_name,
                "confidence": r.confidence,
                "match_method": r.match_method,
                "collection_entry_id": r.collection_entry_id,
                "already_has_price": r.already_has_price,
                "current_acquisition_price": (
                    str(r.current_acquisition_price)
                    if r.current_acquisition_price is not None
                    else None
                ),
                "selected": r.confidence >= 0.85,
            }
        )

    unmatched = []
    for r in report.unmatched:
        item = r.parsed_item
        unmatched.append(
            {
                "card_name_parsed": _format_parsed_name(item),
                "set_code_parsed": item.set_code,
                "unit_price": str(item.unit_price),
                "order_number": item.order_number,
                "skip_reason": r.skip_reason or "No matching collection entry found",
            }
        )

    return {
        "total_files": len(valid_files),
        "total_orders": len(all_orders),
        "total_items_parsed": report.total_parsed,
        "total_items_matched": len(matches),
        "total_items_unmatched": len(unmatched),
        "total_sealed_skipped": sealed_count,
        "matches": matches,
        "unmatched": unmatched,
        "warnings": all_warnings,
    }


@router.post("/apply")
async def apply_purchases(
    body: dict,
    user=Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Apply selected matches to update acquisition_price and acquired_at.

    Uses a two-phase approach for atomicity:
    1. Validate all entries (ownership, price, date) via reads.
    2. Apply all updates in a single transaction so either all succeed
       or none are committed.
    """
    match_list = body.get("matches", [])
    if not match_list:
        raise HTTPException(status_code=400, detail="No matches provided")

    user_id = str(user.id)
    skipped: list[dict] = []

    # --- Phase 1: Validate all entries and prepare updates ---
    pending_updates: list[dict] = []  # [{entry_id, updates, card_name, price, acquired_at}]

    for m in match_list:
        entry_id = m.get("collection_entry_id")
        if entry_id is None:
            continue

        overwrite = m.get("overwrite", False)
        price_str = m.get("acquisition_price", "0")
        date_str = m.get("acquired_at")

        # Validate price
        try:
            price = Decimal(str(price_str))
        except (InvalidOperation, ValueError):
            skipped.append(
                {
                    "collection_entry_id": entry_id,
                    "card_name": "",
                    "reason": f"Invalid price: {price_str}",
                }
            )
            continue

        # Parse date
        acquired_at: date | None = None
        if date_str:
            try:
                acquired_at = datetime.strptime(str(date_str), "%Y-%m-%d").date()
            except ValueError:
                acquired_at = None

        # Verify ownership
        entry = repo.get_collection_entry(entry_id)
        if entry is None:
            raise HTTPException(
                status_code=404,
                detail=f"Collection entry {entry_id} not found",
            )
        if entry.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail=f"Collection entry {entry_id} does not belong to you",
            )

        # Check existing price
        card_name = entry.name_en or entry.name_pt or ""
        if entry.acquisition_price is not None and not overwrite:
            skipped.append(
                {
                    "collection_entry_id": entry_id,
                    "card_name": card_name,
                    "reason": "Already has price and overwrite=false",
                }
            )
            continue

        updates: dict = {"acquisition_price": price}
        if acquired_at:
            updates["acquired_at"] = acquired_at

        pending_updates.append(
            {
                "entry_id": entry_id,
                "user_id": user_id,
                "updates": updates,
                "card_name": card_name,
                "price": price,
                "acquired_at": acquired_at,
            }
        )

    # --- Phase 2: Apply all updates in a single atomic transaction ---
    applied: list[dict] = []

    if pending_updates:
        with repo.transaction() as txn_session:
            for pu in pending_updates:
                repo.update_collection_entry(
                    pu["entry_id"],
                    pu["user_id"],
                    pu["updates"],
                    session=txn_session,
                )
                applied.append(
                    {
                        "collection_entry_id": pu["entry_id"],
                        "card_name": pu["card_name"],
                        "acquisition_price": str(pu["price"]),
                        "acquired_at": (
                            pu["acquired_at"].isoformat() if pu["acquired_at"] else None
                        ),
                    }
                )

    return {
        "total_applied": len(applied),
        "total_skipped": len(skipped),
        "applied": applied,
        "skipped": skipped,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_full_collection(repo: Repository, user_id: str) -> list[UserCollectionRow]:
    """Load all collection entries for a user (unpaginated)."""
    entries: list[UserCollectionRow] = []
    offset = 0
    batch_size = 500
    while True:
        batch = repo.list_collection(
            user_id,
            sort_by="name",
            sort_dir="asc",
            offset=offset,
            limit=batch_size,
        )
        entries.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
    return entries


def _format_parsed_name(item) -> str:
    """Build a display name from parsed item fields."""
    parts = []
    if item.card_name_pt:
        parts.append(item.card_name_pt)
    if item.card_name_en:
        parts.append(item.card_name_en)
    if len(parts) == 2:
        return f"{parts[0]} / {parts[1]}"
    return parts[0] if parts else "Unknown"

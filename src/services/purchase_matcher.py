"""Match parsed purchase items to user collection entries.

Given a list of :class:`ParsedPurchaseItem` (from ``purchase_parser``) and
the user's collection rows, this module attempts to find the best matching
``UserCollectionRow`` for each parsed item using a cascading strategy:

1. **Exact** -- name + set_code + collector_number  (confidence 1.0)
2. **Name + set** -- name + set_code                (confidence 0.95)
3. **Name + CN** -- name + collector_number          (confidence 0.85)
4. **Name only** -- just the card name               (confidence 0.7)
5. **No match**                                      (confidence 0.0)

Name comparisons are accent-insensitive and case-insensitive using stdlib
``unicodedata`` -- no external dependency required.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal

from src.database.models import UserCollectionRow
from src.services.purchase_parser import ParsedPurchaseItem

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class MatchResult:
    """Result of matching a single parsed item to a collection entry."""

    parsed_item: ParsedPurchaseItem
    collection_entry_id: int | None = None
    collection_entry_name: str | None = None
    collection_set_code: str | None = None
    collection_quantity: int | None = None
    confidence: float = 0.0
    match_method: str = "none"
    skip_reason: str | None = None
    already_has_price: bool = False
    current_acquisition_price: Decimal | None = None
    duplicate_entry_ids: list[int] = field(default_factory=list)


@dataclass
class MatchReport:
    """Aggregated results of the matching process."""

    matched: list[MatchResult] = field(default_factory=list)
    unmatched: list[MatchResult] = field(default_factory=list)
    total_parsed: int = 0
    total_matched: int = 0
    total_skipped: int = 0
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Name normalisation (stdlib only -- no unidecode)
# ---------------------------------------------------------------------------


def normalize_name(name: str) -> str:
    """Accent-insensitive, case-insensitive normalisation.

    Strips combining marks (diacritics) so that ``Dragao`` matches
    ``Dragao`` etc.
    """
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_text.lower().strip()


def _front_face(name: str) -> str:
    """Return the front face name from a DFC (``Front // Back``)."""
    if " // " in name:
        return name.split(" // ", 1)[0].strip()
    return name


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------


def _build_indexes(
    entries: list[UserCollectionRow],
) -> tuple[
    dict[tuple[str, str], list[UserCollectionRow]],  # (name_en, set_code)
    dict[tuple[str, str], list[UserCollectionRow]],  # (name_pt, set_code)
    dict[tuple[str, str], list[UserCollectionRow]],  # (name_en, cn)
    dict[str, list[UserCollectionRow]],  # name_en only
    dict[str, list[UserCollectionRow]],  # name_pt only
]:
    """Build multiple lookup indexes for cascading match."""
    idx_name_en_set: dict[tuple[str, str], list[UserCollectionRow]] = {}
    idx_name_pt_set: dict[tuple[str, str], list[UserCollectionRow]] = {}
    idx_name_en_cn: dict[tuple[str, str], list[UserCollectionRow]] = {}
    idx_name_en: dict[str, list[UserCollectionRow]] = {}
    idx_name_pt: dict[str, list[UserCollectionRow]] = {}

    for entry in entries:
        # Normalised English name
        if entry.name_en:
            norm_en = normalize_name(entry.name_en)
            # Also index front face for DFC
            norm_en_front = normalize_name(_front_face(entry.name_en))

            for n in {norm_en, norm_en_front}:
                if entry.set_code:
                    key_set = (n, entry.set_code.lower())
                    idx_name_en_set.setdefault(key_set, []).append(entry)

                if entry.collector_number:
                    key_cn = (n, entry.collector_number.lower())
                    idx_name_en_cn.setdefault(key_cn, []).append(entry)

                idx_name_en.setdefault(n, []).append(entry)

        # Normalised Portuguese name
        if entry.name_pt:
            norm_pt = normalize_name(entry.name_pt)
            if entry.set_code:
                key_set = (norm_pt, entry.set_code.lower())
                idx_name_pt_set.setdefault(key_set, []).append(entry)
            idx_name_pt.setdefault(norm_pt, []).append(entry)

    return idx_name_en_set, idx_name_pt_set, idx_name_en_cn, idx_name_en, idx_name_pt


# ---------------------------------------------------------------------------
# Best candidate selection
# ---------------------------------------------------------------------------


def _pick_best(candidates: list[UserCollectionRow]) -> UserCollectionRow:
    """Choose the best candidate from a list of matches.

    Prefers entries without existing acquisition_price, then by lowest id.
    """
    if len(candidates) == 1:
        return candidates[0]

    # Prefer entries without existing price
    without_price = [e for e in candidates if e.acquisition_price is None]
    pool = without_price if without_price else candidates

    return min(pool, key=lambda e: e.id)


# ---------------------------------------------------------------------------
# Core matching
# ---------------------------------------------------------------------------


def match_purchases(
    parsed_items: list[ParsedPurchaseItem],
    collection_entries: list[UserCollectionRow],
) -> MatchReport:
    """Match parsed purchase items to collection entries.

    Parameters
    ----------
    parsed_items:
        Items extracted from purchase HTML by the parser.
    collection_entries:
        The user's collection rows (pre-loaded by the caller).

    Returns
    -------
    MatchReport
        With ``matched`` (confidence > 0) and ``unmatched`` lists.
    """
    report = MatchReport(total_parsed=len(parsed_items))

    if not collection_entries:
        for item in parsed_items:
            report.unmatched.append(
                MatchResult(
                    parsed_item=item,
                    skip_reason="No collection entries found",
                )
            )
        return report

    (
        idx_name_en_set,
        idx_name_pt_set,
        idx_name_en_cn,
        idx_name_en,
        idx_name_pt,
    ) = _build_indexes(collection_entries)

    # Track which entry_ids have been matched to detect duplicates
    matched_entry_ids: dict[int, list[MatchResult]] = {}

    for item in parsed_items:
        result = _match_single_item(
            item,
            idx_name_en_set,
            idx_name_pt_set,
            idx_name_en_cn,
            idx_name_en,
            idx_name_pt,
        )

        if result.confidence > 0 and result.collection_entry_id is not None:
            report.matched.append(result)
            report.total_matched += 1

            # Track for duplicate detection
            eid = result.collection_entry_id
            matched_entry_ids.setdefault(eid, []).append(result)
        else:
            report.unmatched.append(result)

    # Flag duplicates
    for eid, results in matched_entry_ids.items():
        if len(results) > 1:
            all_ids = [eid]
            for r in results:
                r.duplicate_entry_ids = all_ids
            report.warnings.append(f"Multiple parsed items matched collection entry #{eid}")

    return report


def _match_single_item(
    item: ParsedPurchaseItem,
    idx_name_en_set: dict[tuple[str, str], list[UserCollectionRow]],
    idx_name_pt_set: dict[tuple[str, str], list[UserCollectionRow]],
    idx_name_en_cn: dict[tuple[str, str], list[UserCollectionRow]],
    idx_name_en: dict[str, list[UserCollectionRow]],
    idx_name_pt: dict[str, list[UserCollectionRow]],
) -> MatchResult:
    """Try cascading match strategies for a single item."""
    # Normalise parsed names
    norm_names_en: list[str] = []
    norm_names_pt: list[str] = []

    if item.card_name_en:
        norm_names_en.append(normalize_name(item.card_name_en))
        norm_names_en.append(normalize_name(_front_face(item.card_name_en)))
    if item.card_name_pt:
        norm_names_pt.append(normalize_name(item.card_name_pt))
        norm_names_pt.append(normalize_name(_front_face(item.card_name_pt)))
    # Also try pt name as en (cross-language match)
    if item.card_name_pt:
        norm_names_en.append(normalize_name(item.card_name_pt))

    # Deduplicate
    norm_names_en = list(dict.fromkeys(norm_names_en))
    norm_names_pt = list(dict.fromkeys(norm_names_pt))

    set_code_lower = item.set_code.lower() if item.set_code else None
    cn_lower = item.collector_number.lower() if item.collector_number else None

    # --- Strategy 1: Exact (name + set + CN) → confidence 1.0 ---
    if set_code_lower and cn_lower:
        for name in norm_names_en:
            key = (name, set_code_lower)
            candidates = idx_name_en_set.get(key, [])
            cn_matches = [
                e
                for e in candidates
                if e.collector_number and e.collector_number.lower() == cn_lower
            ]
            if cn_matches:
                entry = _pick_best(cn_matches)
                return _build_result(item, entry, confidence=1.0, method="exact")

        for name in norm_names_pt:
            key = (name, set_code_lower)
            candidates = idx_name_pt_set.get(key, [])
            cn_matches = [
                e
                for e in candidates
                if e.collector_number and e.collector_number.lower() == cn_lower
            ]
            if cn_matches:
                entry = _pick_best(cn_matches)
                return _build_result(item, entry, confidence=1.0, method="exact")

    # --- Strategy 2: Name + set (no CN) → confidence 0.95 ---
    if set_code_lower:
        for name in norm_names_en:
            key = (name, set_code_lower)
            candidates = idx_name_en_set.get(key, [])
            if candidates:
                entry = _pick_best(candidates)
                return _build_result(item, entry, confidence=0.95, method="name_set")

        for name in norm_names_pt:
            key = (name, set_code_lower)
            candidates = idx_name_pt_set.get(key, [])
            if candidates:
                entry = _pick_best(candidates)
                return _build_result(item, entry, confidence=0.95, method="name_set")

    # --- Strategy 3: Name + CN (no set) → confidence 0.85 ---
    if cn_lower:
        for name in norm_names_en:
            key = (name, cn_lower)
            candidates = idx_name_en_cn.get(key, [])
            if candidates:
                entry = _pick_best(candidates)
                return _build_result(item, entry, confidence=0.85, method="name_cn")

    # --- Strategy 4: Name only → confidence 0.7 ---
    for name in norm_names_en:
        candidates = idx_name_en.get(name, [])
        if candidates:
            entry = _pick_best(candidates)
            return _build_result(item, entry, confidence=0.7, method="name_only")

    for name in norm_names_pt:
        candidates = idx_name_pt.get(name, [])
        if candidates:
            entry = _pick_best(candidates)
            return _build_result(item, entry, confidence=0.7, method="name_only")

    # --- No match ---
    return MatchResult(
        parsed_item=item,
        skip_reason="No matching collection entry found",
    )


def _build_result(
    item: ParsedPurchaseItem,
    entry: UserCollectionRow,
    *,
    confidence: float,
    method: str,
) -> MatchResult:
    """Build a :class:`MatchResult` from a parsed item and matched entry."""
    return MatchResult(
        parsed_item=item,
        collection_entry_id=entry.id,
        collection_entry_name=entry.name_en or entry.name_pt,
        collection_set_code=entry.set_code,
        collection_quantity=entry.quantity,
        confidence=confidence,
        match_method=method,
        already_has_price=entry.acquisition_price is not None,
        current_acquisition_price=entry.acquisition_price,
    )

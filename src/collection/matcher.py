"""Pure matching logic: link a collection entry to MYP search results."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.models import MypSearchResult


@dataclass
class CollectionEntry:
    """Lightweight representation of a collection card for matching.

    Avoids coupling the matcher to SQLAlchemy models.  Callers can
    construct this from ``UserCollectionRow`` or any other source.
    """

    set_code: str
    collector_number: str
    name_en: str | None = None
    name_pt: str | None = None


@dataclass
class MatchResult:
    """Outcome of matching a collection entry against MYP search results."""

    status: str  # "matched" | "ambiguous" | "unmatched"
    collection_entry: CollectionEntry
    myp_result: MypSearchResult | None  # best match, if any
    confidence: str  # "sku_exact" | "name_set" | "name_only" | "none"
    candidates: list[MypSearchResult] = field(default_factory=list)


def match_collection_card(
    entry: CollectionEntry,
    search_results: list[MypSearchResult],
) -> MatchResult:
    """Score and select the best MYP match for a collection entry.

    Matching priority (highest to lowest):
    1. **SKU-exact** -- ``set_code`` + ``collector_number`` from the MYP
       search result's parsed SKU match the collection entry.
    2. **Name + set** -- Exactly one search result matches by ``name``
       (case-insensitive, stripped) AND ``set_code``.
    3. **Name only** -- Exactly one search result matches by ``name``
       (case-insensitive, stripped) regardless of set.
    4. **Ambiguous** -- Multiple candidates match by name but none by SKU.
    5. **Unmatched** -- Zero search results or no name/SKU overlap.

    All comparisons are pure; no DB or network calls.
    """
    if not search_results:
        return MatchResult(
            status="unmatched",
            collection_entry=entry,
            myp_result=None,
            confidence="none",
            candidates=[],
        )

    # --- 1. SKU-based matching (highest confidence) ---
    sku_match = _try_sku_match(entry, search_results)
    if sku_match is not None:
        return MatchResult(
            status="matched",
            collection_entry=entry,
            myp_result=sku_match,
            confidence="sku_exact",
            candidates=search_results,
        )

    # --- 2-4. Name-based matching (fallback) ---
    return _try_name_match(entry, search_results)


# ── internal helpers ─────────────────────────────────────────────


def _try_sku_match(
    entry: CollectionEntry,
    results: list[MypSearchResult],
) -> MypSearchResult | None:
    """Return the first result whose parsed SKU matches the entry exactly.

    Comparison is case-insensitive for ``set_code`` and exact string for
    ``collector_number``.
    """
    entry_set = entry.set_code.lower()
    entry_num = entry.collector_number

    for r in results:
        if r.set_code is None or r.collector_number is None:
            continue
        if r.set_code.lower() == entry_set and r.collector_number == entry_num:
            return r

    return None


def _try_name_match(
    entry: CollectionEntry,
    results: list[MypSearchResult],
) -> MatchResult:
    """Fall back to name-based matching when no SKU match was found."""
    if not entry.name_en and not entry.name_pt:
        return MatchResult(
            status="unmatched",
            collection_entry=entry,
            myp_result=None,
            confidence="none",
            candidates=results,
        )

    entry_names: set[str] = set()
    if entry.name_en:
        entry_names.add(_normalize(entry.name_en))
    if entry.name_pt:
        entry_names.add(_normalize(entry.name_pt))

    entry_set = entry.set_code.lower()

    name_matches: list[MypSearchResult] = []
    for r in results:
        if _normalize(r.name) in entry_names:
            name_matches.append(r)

    if not name_matches:
        return MatchResult(
            status="unmatched",
            collection_entry=entry,
            myp_result=None,
            confidence="none",
            candidates=results,
        )

    # Among name matches, filter by set_code
    name_set_matches = [
        r for r in name_matches if r.set_code is not None and r.set_code.lower() == entry_set
    ]

    if len(name_set_matches) == 1:
        return MatchResult(
            status="matched",
            collection_entry=entry,
            myp_result=name_set_matches[0],
            confidence="name_set",
            candidates=results,
        )

    # Exactly one name match (regardless of set) → name_only
    if len(name_matches) == 1:
        return MatchResult(
            status="matched",
            collection_entry=entry,
            myp_result=name_matches[0],
            confidence="name_only",
            candidates=results,
        )

    # Multiple name matches, none narrowed by set → ambiguous
    return MatchResult(
        status="ambiguous",
        collection_entry=entry,
        myp_result=None,
        confidence="none",
        candidates=results,
    )


def _normalize(name: str) -> str:
    """Lowercase and strip whitespace for case-insensitive name comparison."""
    return name.strip().lower()

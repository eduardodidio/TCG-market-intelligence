"""Dry-run match report — checks MYP coverage for user collection cards."""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from src.collection.converter import row_to_collection_entry
from src.collection.matcher import MatchResult, match_collection_card
from src.database.models import UserCollectionRow
from src.database.repository import Repository
from src.providers.myp.provider import MypCardsProvider, MypConfig

log = structlog.get_logger()


@dataclass
class MatchReportSummary:
    """Aggregate counts for a match report run."""

    total: int = 0
    matched_sku: int = 0
    matched_name_set: int = 0
    matched_name_only: int = 0
    ambiguous: int = 0
    unmatched: int = 0
    skipped_no_name: int = 0
    errors: int = 0
    results: list[MatchResult] = field(default_factory=list)

    @property
    def matched_total(self) -> int:
        return self.matched_sku + self.matched_name_set + self.matched_name_only


def _pct(n: int, total: int) -> str:
    """Format a percentage string with one decimal place."""
    if total == 0:
        return " 0.0%"
    return f"{n / total * 100:5.1f}%"


def _unmatched_sets(summary: MatchReportSummary) -> list[tuple[str, int]]:
    """Count unmatched cards per set_code, sorted descending."""
    counter: Counter[str] = Counter()
    for r in summary.results:
        if r.status == "unmatched":
            counter[r.collection_entry.set_code] += 1
    return counter.most_common()


async def run_match_report(
    db_url: str = "sqlite:///tcg_market.db",
    limit: int | None = None,
    delay: float = 1.0,
    concurrency: int = 3,
    output: str | None = None,
) -> MatchReportSummary:
    """Run the dry-run match report.

    Reads all ``user_collection`` entries from the DB, searches MYP for
    each card, and returns a summary of match/ambiguous/unmatched counts.

    This is a **read-only** operation: no database writes occur.

    Args:
        db_url: Database connection string.
        limit: Maximum number of cards to process (for testing).
        delay: Seconds between requests.
        concurrency: Max concurrent searches.
        output: If set, write detailed JSON report to this path.
    """
    config = MypConfig(delay_seconds=delay)
    provider = MypCardsProvider(config)
    repo = Repository(db_url)
    summary = MatchReportSummary()

    try:
        entries = repo.get_all_collection_entries()
        summary.total = len(entries)
        log.info("match_report_start", total_entries=summary.total)

        if limit:
            entries = entries[:limit]
            log.info("limit_applied", processing=len(entries))

        total = len(entries)
        sem = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()

        async def process_entry(row: UserCollectionRow, index: int) -> None:
            async with sem:
                entry = row_to_collection_entry(row)

                if not entry.name_en:
                    async with lock:
                        summary.skipped_no_name += 1
                    log.info(
                        "skipped_no_name",
                        index=index,
                        total=total,
                        set_code=entry.set_code,
                        collector_number=entry.collector_number,
                    )
                    return

                log.info(
                    "matching_card",
                    index=index,
                    total=total,
                    name=entry.name_en,
                    set_code=entry.set_code,
                )

                try:
                    search_results = await provider.search_card(entry.name_en)
                except Exception as e:
                    async with lock:
                        summary.errors += 1
                    log.warning(
                        "search_error",
                        name=entry.name_en,
                        error=str(e),
                    )
                    return

                result = match_collection_card(entry, search_results)

                async with lock:
                    summary.results.append(result)
                    if result.status == "matched":
                        if result.confidence == "sku_exact":
                            summary.matched_sku += 1
                        elif result.confidence == "name_set":
                            summary.matched_name_set += 1
                        elif result.confidence == "best_effort":
                            summary.ambiguous += 1
                        else:
                            summary.matched_name_only += 1
                    else:
                        summary.unmatched += 1

        tasks = [process_entry(row, i) for i, row in enumerate(entries, 1)]
        await asyncio.gather(*tasks)

        if output:
            _write_json_report(summary, output)

        return summary

    finally:
        await provider.close()


def format_report(summary: MatchReportSummary) -> str:
    """Build the human-readable report text."""
    total = summary.total
    sku_pct = _pct(summary.matched_sku, total)
    ns_pct = _pct(summary.matched_name_set, total)
    no_pct = _pct(summary.matched_name_only, total)
    amb_pct = _pct(summary.ambiguous, total)
    unm_pct = _pct(summary.unmatched, total)

    lines = [
        "",
        "=== Collection Match Report ===",
        f"Total collection cards: {total}",
        f"  Matched (SKU exact):  {summary.matched_sku:>3} ({sku_pct})",
        f"  Matched (name+set):   {summary.matched_name_set:>3} ({ns_pct})",
        f"  Matched (name only):  {summary.matched_name_only:>3} ({no_pct})",
        f"  Ambiguous:            {summary.ambiguous:>3} ({amb_pct})",
        f"  Unmatched:            {summary.unmatched:>3} ({unm_pct})",
    ]
    if summary.skipped_no_name > 0:
        skip_pct = _pct(summary.skipped_no_name, total)
        lines.append(f"  Skipped (no name):    {summary.skipped_no_name:>3} ({skip_pct})")
    if summary.errors > 0:
        lines.append(f"  Errors:               {summary.errors:>3} ({_pct(summary.errors, total)})")
    lines.append("=" * 31)

    # Top unmatched sets
    unmatched = _unmatched_sets(summary)
    if unmatched:
        lines.append("")
        lines.append("Top unmatched sets:")
        for set_code, count in unmatched[:10]:
            lines.append(f"  {set_code} ({count} cards)")

    lines.append("")
    return "\n".join(lines)


def _write_json_report(summary: MatchReportSummary, path: str) -> None:
    """Write the detailed match results to a JSON file."""
    data = {
        "total": summary.total,
        "matched_sku": summary.matched_sku,
        "matched_name_set": summary.matched_name_set,
        "matched_name_only": summary.matched_name_only,
        "ambiguous": summary.ambiguous,
        "unmatched": summary.unmatched,
        "skipped_no_name": summary.skipped_no_name,
        "errors": summary.errors,
        "results": [
            {
                "status": r.status,
                "confidence": r.confidence,
                "entry": {
                    "set_code": r.collection_entry.set_code,
                    "collector_number": r.collection_entry.collector_number,
                    "name_en": r.collection_entry.name_en,
                },
                "myp_match": {
                    "external_id": r.myp_result.external_id,
                    "name": r.myp_result.name,
                    "url": r.myp_result.url,
                    "sku": r.myp_result.sku,
                }
                if r.myp_result
                else None,
                "candidates_count": len(r.candidates),
            }
            for r in summary.results
        ],
    }
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("json_report_written", path=path, entries=len(summary.results))

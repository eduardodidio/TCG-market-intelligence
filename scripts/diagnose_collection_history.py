"""Read-only diagnostic for F176: why collection-card price history is empty.

Usage:
    python scripts/diagnose_collection_history.py --entry-id 123
    python scripts/diagnose_collection_history.py --user-id <uid> --sample 20 --json out.json
    python scripts/diagnose_collection_history.py --db sqlite:///tcg_market.db --sample 50

For each sampled ``user_collection`` entry it measures:
    1. The candidate history keys: the card's ``source_cards`` plus the
       direct keys written by the Liga sweep / refresh / scan / manual price
       (``liga_{card_id}``, ``liga_{card_id}_foil``, ``manual_{card_id}``).
    2. Every ``price_observations`` series found under those keys, grouped by
       ``(source, external_id)``: count, first/last date, distinct days in the
       last 30/90 days.
    3. What ``GET /collection/{id}/history`` returns TODAY (replica of
       ``get_collection_history``: source_cards x ``[sc.source,
       'jsonld_snapshot']``) vs. what exists in the window -> lost points.
    4. Same-day duplicates (H5), foil/normal mixing (H4), fabricated
       ``daily_snapshot`` rows before the first real observation (H6) and
       what the planned F176 key resolver (shard 02, inlined) would return.

This script is READ-ONLY: it only issues SELECTs (on PostgreSQL every
transaction is additionally marked ``READ ONLY``). It does not create tables
(no ``Repository(...)`` construction in ``main``) and it is intentionally not
registered in src/cli/main.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from src.collection.converter import is_foil_entry
from src.database.models import PriceObservationRow, SourceCardRow, UserCollectionRow

SNAPSHOT_SOURCE = "daily_snapshot"
JSONLD_SOURCE = "jsonld_snapshot"
DEFAULT_SAMPLE = 20
DEFAULT_DAYS = 30


class EntryNotFoundError(LookupError):
    """Raised when a --entry-id does not exist in user_collection."""


class _ReadOnlyDB:
    """Minimal stand-in for Repository: exposes ``engine`` only, no DDL."""

    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, echo=False)


@contextmanager
def _read_session(repo: Any) -> Iterator[Session]:
    """Session that never commits; READ ONLY transaction on PostgreSQL."""
    with Session(repo.engine) as session:
        if repo.engine.dialect.name == "postgresql":
            session.execute(text("SET TRANSACTION READ ONLY"))
        try:
            yield session
        finally:
            session.rollback()


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------


def _is_foil_key(external_id: str) -> bool:
    return external_id.endswith("_foil")


def candidate_keys(card_id: int, source_cards: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """All (source, external_id) keys that may hold history for ``card_id``.

    ``source_cards`` come first (what the current endpoint reads), then the
    direct keys that have no ``source_cards`` row. Deduplicated, stable order.
    """
    keys: list[tuple[str, str]] = list(source_cards)
    keys += [
        ("liga", f"liga_{card_id}"),
        ("liga", f"liga_{card_id}_foil"),
        ("manual", f"manual_{card_id}"),
    ]
    return list(dict.fromkeys(keys))


def _resolver_keys(
    card_id: int, source_cards: list[tuple[str, str]], is_foil: bool
) -> list[tuple[str, str]]:
    """Inline replica of the planned F176 resolver (shard 02).

    Kept local on purpose: T03 (``src/collection/price_history_keys.py``) does
    not exist yet in Wave 0.
    """
    suffix = "_foil" if is_foil else ""
    keys = [
        ("liga", f"liga_{card_id}{suffix}"),
        (SNAPSHOT_SOURCE, f"liga_{card_id}{suffix}"),
        ("manual", f"manual_{card_id}"),
        (SNAPSHOT_SOURCE, f"manual_{card_id}"),
    ]
    for source, ext in source_cards:
        if _is_foil_key(ext) != is_foil:
            continue
        keys += [(source, ext), (JSONLD_SOURCE, ext), (SNAPSHOT_SOURCE, ext)]
    return list(dict.fromkeys(keys))


# ---------------------------------------------------------------------------
# Per-entry diagnosis
# ---------------------------------------------------------------------------


def _empty_diagnosis(entry: UserCollectionRow, is_foil: bool) -> dict:
    return {
        "entry_id": entry.id,
        "user_id": entry.user_id,
        "card_id": entry.card_id,
        "name": entry.name_en or entry.name_pt,
        "set_code": entry.set_code,
        "collector_number": entry.collector_number,
        "extras": entry.extras,
        "is_foil": is_foil,
        "status": "unlinked",
        "source_cards": [],
        "series": [],
        "available_points": 0,
        "available_days": 0,
        "available_by_source": {},
        "current_endpoint_points": 0,
        "current_endpoint_days": 0,
        "current_endpoint_duplicate_dates": 0,
        "lost_points": 0,
        "lost_by_source": {},
        "duplicate_dates": 0,
        "has_liga_normal": False,
        "has_liga_foil": False,
        "mixed_variants": False,
        "current_endpoint_mixes_variants": False,
        "snapshots_before_first_real": 0,
        "backfilled_snapshots": 0,
        "real_days_window": 0,
        "snapshot_days_window": 0,
        "last_daily_snapshot": None,
        "resolver_days": 0,
        "flags": {f"H{i}": False for i in range(1, 7)},
    }


def collect_entry_diagnosis(repo: Any, entry_id: int, days: int = DEFAULT_DAYS) -> dict:
    """Diagnose one collection entry. SELECT-only.

    Raises ``EntryNotFoundError`` when ``entry_id`` does not exist.
    """
    today = date.today()
    cutoff = today - timedelta(days=days)
    cutoff_30 = today - timedelta(days=30)
    cutoff_90 = today - timedelta(days=90)

    with _read_session(repo) as session:
        entry = session.get(UserCollectionRow, entry_id)
        if entry is None:
            raise EntryNotFoundError(f"collection entry {entry_id} not found")

        is_foil = is_foil_entry(entry.extras)
        diag = _empty_diagnosis(entry, is_foil)
        if entry.card_id is None:
            return diag

        card_id = entry.card_id
        sc_rows = session.execute(
            select(SourceCardRow.source, SourceCardRow.external_id)
            .where(SourceCardRow.card_id == card_id)
            .order_by(SourceCardRow.id)
        ).all()
        source_cards = [(s, e) for s, e in sc_rows]
        keys = candidate_keys(card_id, source_cards)
        ext_ids = sorted({e for _, e in keys})

        rows = session.execute(
            select(
                PriceObservationRow.source,
                PriceObservationRow.external_id,
                PriceObservationRow.observed_at,
                PriceObservationRow.created_at,
            ).where(PriceObservationRow.external_id.in_(ext_ids))
        ).all()

    obs = [(s, e, d) for s, e, d, _ in rows]
    # run_daily_snapshot always writes observed_at == today; a daily_snapshot
    # row dated before its insertion day can only come from backfill_snapshots.
    backfilled = sum(
        1 for s, _, d, created in rows if s == SNAPSHOT_SOURCE and created and d < created.date()
    )

    diag["status"] = "linked"
    diag["source_cards"] = [{"source": s, "external_id": e} for s, e in source_cards]

    # Series overview (all time)
    by_series: dict[tuple[str, str], list[date]] = defaultdict(list)
    for source, ext, observed_at in obs:
        by_series[(source, ext)].append(observed_at)
    diag["series"] = [
        {
            "source": source,
            "external_id": ext,
            "count": len(dates),
            "first": min(dates).isoformat(),
            "last": max(dates).isoformat(),
            "days_30": len({d for d in dates if d >= cutoff_30}),
            "days_90": len({d for d in dates if d >= cutoff_90}),
        }
        for (source, ext), dates in sorted(by_series.items())
    ]

    window = [(s, e, d) for s, e, d in obs if d >= cutoff]

    # What get_collection_history returns today
    endpoint_pairs = {(s, e) for sc_src, e in source_cards for s in (sc_src, JSONLD_SOURCE)}
    endpoint = [(s, e, d) for s, e, d in window if (s, e) in endpoint_pairs]
    lost = [(s, e, d) for s, e, d in window if (s, e) not in endpoint_pairs]

    endpoint_dates = Counter(d for _, _, d in endpoint)
    window_dates = Counter(d for _, _, d in window)

    diag["available_points"] = len(window)
    diag["available_days"] = len(window_dates)
    diag["available_by_source"] = dict(Counter(s for s, _, _ in window))
    diag["current_endpoint_points"] = len(endpoint)
    diag["current_endpoint_days"] = len(endpoint_dates)
    diag["current_endpoint_duplicate_dates"] = sum(1 for c in endpoint_dates.values() if c > 1)
    diag["lost_points"] = len(lost)
    diag["lost_by_source"] = dict(Counter(s for s, _, _ in lost))
    diag["duplicate_dates"] = sum(1 for c in window_dates.values() if c > 1)

    # H4 — variant mixing
    ext_with_data = {e for _, e in by_series}
    has_foil = any(_is_foil_key(e) for e in ext_with_data)
    has_normal = any(not _is_foil_key(e) for e in ext_with_data)
    diag["has_liga_normal"] = f"liga_{card_id}" in ext_with_data
    diag["has_liga_foil"] = f"liga_{card_id}_foil" in ext_with_data
    diag["mixed_variants"] = has_foil and has_normal
    endpoint_ext = {e for _, e, _ in endpoint}
    diag["current_endpoint_mixes_variants"] = any(_is_foil_key(e) != is_foil for e in endpoint_ext)

    # H3 / H6 — snapshot density and fabricated backfill
    first_real: dict[str, date] = {}
    for source, ext, observed_at in obs:
        if source == SNAPSHOT_SOURCE:
            continue
        if ext not in first_real or observed_at < first_real[ext]:
            first_real[ext] = observed_at
    snapshot_dates = [(e, d) for s, e, d in obs if s == SNAPSHOT_SOURCE]
    diag["snapshots_before_first_real"] = sum(
        1 for e, d in snapshot_dates if e not in first_real or d < first_real[e]
    )
    diag["backfilled_snapshots"] = backfilled
    diag["real_days_window"] = len({d for s, _, d in window if s != SNAPSHOT_SOURCE})
    diag["snapshot_days_window"] = len({d for s, _, d in window if s == SNAPSHOT_SOURCE})
    diag["last_daily_snapshot"] = (
        max(d for _, d in snapshot_dates).isoformat() if snapshot_dates else None
    )

    # Planned resolver (shard 02): 1 point per day over the variant's keys
    resolver = set(_resolver_keys(card_id, source_cards, is_foil))
    diag["resolver_days"] = len({d for s, e, d in window if (s, e) in resolver})

    lost_sources = diag["lost_by_source"]
    diag["flags"] = {
        "H1": any(s == "liga" and e.startswith(f"liga_{card_id}") for s, e, _ in lost),
        "H2": lost_sources.get(SNAPSHOT_SOURCE, 0) + lost_sources.get("manual", 0) > 0,
        "H3": diag["snapshot_days_window"] == 0 and diag["real_days_window"] < 2,
        "H4": diag["mixed_variants"] or diag["current_endpoint_mixes_variants"],
        "H5": diag["duplicate_dates"] > 0,
        "H6": diag["snapshots_before_first_real"] + backfilled > 0,
    }
    return diag


# ---------------------------------------------------------------------------
# Aggregation (pure)
# ---------------------------------------------------------------------------


def _pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 1) if whole else 0.0


def summarize(diagnoses: list[dict]) -> dict:
    """Aggregate per-entry diagnoses. Pure; safe on an empty list."""
    total = len(diagnoses)
    linked = [d for d in diagnoses if d["status"] == "linked"]
    foil = [d for d in diagnoses if d["is_foil"]]
    sources: Counter[str] = Counter()
    lost_sources: Counter[str] = Counter()
    for d in linked:
        sources.update(d["available_by_source"])
        lost_sources.update(d["lost_by_source"])
    snapshots = [d["last_daily_snapshot"] for d in linked if d["last_daily_snapshot"]]

    return {
        "entries": total,
        "linked": len(linked),
        "unlinked": total - len(linked),
        "pct_zero_current_endpoint": _pct(
            sum(1 for d in diagnoses if d["current_endpoint_points"] == 0), total
        ),
        "pct_current_ge2_days": _pct(
            sum(1 for d in diagnoses if d["current_endpoint_days"] >= 2), total
        ),
        "pct_resolver_ge2_days": _pct(sum(1 for d in diagnoses if d["resolver_days"] >= 2), total),
        "available_points": sum(d["available_points"] for d in diagnoses),
        "current_endpoint_points": sum(d["current_endpoint_points"] for d in diagnoses),
        "lost_points": sum(d["lost_points"] for d in diagnoses),
        "available_by_source": dict(sources),
        "lost_by_source": dict(lost_sources),
        "backfilled_snapshots": sum(d["backfilled_snapshots"] for d in diagnoses),
        "foil_entries": len(foil),
        "foil_entries_with_liga_foil_series": sum(1 for d in foil if d["has_liga_foil"]),
        "last_daily_snapshot": max(snapshots) if snapshots else None,
        "hypothesis_counts": {
            f"H{i}": sum(1 for d in diagnoses if d["flags"][f"H{i}"]) for i in range(1, 7)
        },
    }


# ---------------------------------------------------------------------------
# Global stats + entry selection (SELECT-only)
# ---------------------------------------------------------------------------


def collect_global_stats(repo: Any, days: int = DEFAULT_DAYS) -> dict:
    """DB-wide numbers: external_id prefixes and daily_snapshot freshness (H3)."""
    cutoff = date.today() - timedelta(days=days)
    ext = PriceObservationRow.external_id
    prefixes = {
        "liga_catalog_%": ext.like("liga\\_catalog\\_%", escape="\\"),
        "liga_%_foil": ext.like("liga\\_%\\_foil", escape="\\")
        & ~ext.like("liga\\_catalog\\_%", escape="\\"),
        "liga_% (normal)": ext.like("liga\\_%", escape="\\")
        & ~ext.like("liga\\_catalog\\_%", escape="\\")
        & ~ext.like("%\\_foil", escape="\\"),
        "manual_%": ext.like("manual\\_%", escape="\\"),
    }
    with _read_session(repo) as session:
        by_prefix = {
            label: session.execute(
                select(func.count()).select_from(PriceObservationRow).where(cond)
            ).scalar_one()
            for label, cond in prefixes.items()
        }
        by_source = dict(
            session.execute(
                select(PriceObservationRow.source, func.count()).group_by(
                    PriceObservationRow.source
                )
            ).all()
        )
        last_snapshot = session.execute(
            select(func.max(PriceObservationRow.observed_at)).where(
                PriceObservationRow.source == SNAPSHOT_SOURCE
            )
        ).scalar_one()
        snapshot_days = session.execute(
            select(func.count(func.distinct(PriceObservationRow.observed_at))).where(
                PriceObservationRow.source == SNAPSHOT_SOURCE,
                PriceObservationRow.observed_at >= cutoff,
            )
        ).scalar_one()
        total_obs = session.execute(
            select(func.count()).select_from(PriceObservationRow)
        ).scalar_one()
    return {
        "price_observations": total_obs,
        "by_prefix": by_prefix,
        "by_source": by_source,
        "last_daily_snapshot": last_snapshot.isoformat() if last_snapshot else None,
        "daily_snapshot_days_in_window": snapshot_days,
    }


def select_entry_ids(repo: Any, user_id: str | None, sample: int) -> list[int]:
    """Return up to ``sample`` entry ids (optionally for one user), id ASC."""
    if sample <= 0:
        return []
    stmt = select(UserCollectionRow.id).order_by(UserCollectionRow.id).limit(sample)
    if user_id is not None:
        stmt = stmt.where(UserCollectionRow.user_id == user_id)
    with _read_session(repo) as session:
        return list(session.execute(stmt).scalars().all())


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _print_report(diagnoses: list[dict], summary: dict, stats: dict, days: int) -> None:
    print(f"\nF176 collection history diagnosis (window={days}d, entries={len(diagnoses)})\n")
    header = (
        f"{'entry':>6} {'card':>6} {'foil':>4} {'sc':>3} {'avail':>5} {'endpt':>5} "
        f"{'lost':>5} {'dup':>4} {'resolv':>6}  flags"
    )
    print(header)
    print("-" * len(header))
    for d in diagnoses:
        flags = ",".join(k for k, v in d["flags"].items() if v) or "-"
        if d["status"] == "unlinked":
            flags = "unlinked"
        print(
            f"{d['entry_id']:>6} {str(d['card_id']):>6} {'Y' if d['is_foil'] else 'N':>4} "
            f"{len(d['source_cards']):>3} {d['available_points']:>5} "
            f"{d['current_endpoint_points']:>5} {d['lost_points']:>5} "
            f"{d['duplicate_dates']:>4} {d['resolver_days']:>6}  {flags}"
        )
    print("\nSummary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print("\nDatabase:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only diagnosis of collection price history (F176)."
    )
    parser.add_argument("--db", default=None, help="DB URL (default: src.config.get_db_url())")
    parser.add_argument("--entry-id", type=int, default=None, help="Diagnose a single entry")
    parser.add_argument("--user-id", default=None, help="Sample entries of this user only")
    parser.add_argument("--sample", type=int, default=DEFAULT_SAMPLE, help="Entries to sample")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="History window in days")
    parser.add_argument("--json", dest="json_path", default=None, help="Write JSON report here")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.days <= 0:
        print("error: --days must be > 0", file=sys.stderr)
        return 2

    if args.db is None:
        from src.config import get_db_url

        args.db = get_db_url()
    repo = _ReadOnlyDB(args.db)

    try:
        if args.entry_id is not None:
            entry_ids = [args.entry_id]
        else:
            entry_ids = select_entry_ids(repo, args.user_id, args.sample)
        diagnoses = [collect_entry_diagnosis(repo, eid, args.days) for eid in entry_ids]
        stats = collect_global_stats(repo, args.days)
    except EntryNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        repo.engine.dispose()

    summary = summarize(diagnoses)
    _print_report(diagnoses, summary, stats, args.days)

    if args.json_path:
        report = {
            "generated_at": date.today().isoformat(),
            "days": args.days,
            "summary": summary,
            "database": stats,
            "entries": diagnoses,
        }
        Path(args.json_path).write_text(json.dumps(report, indent=2, default=str))
        print(f"\nJSON written to {args.json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

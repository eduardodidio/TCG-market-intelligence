"""Read-only diagnostic for F175: measure each price source feeding market trending.

Usage:
    python scripts/diagnose_trending_f175.py --days 7 30 90
    python scripts/diagnose_trending_f175.py --days 30 --user-id 1

For each period, prints:
    1. repo.get_trending_price_data(days) -- cards, total points, elapsed seconds.
    2. Direct count of price_observations for source IN ('liga', 'manual') with
       external_id LIKE 'liga_%%' / 'manual_%%' (excluding 'liga_catalog_%%') in the
       period -- rows, distinct external_ids, elapsed.
    3. compute_trending_score + rank_trending over (1) -- number of gainers/losers.
    4. If --user-id is given, the same as (1)/(3) but via
       repo.get_trending_price_data_for_user.

This script is READ-ONLY: it only issues SELECTs. No writes, no cache
invalidation, and it is intentionally not registered in src/cli/main.py.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from src.analytics.trending import compute_trending_score, rank_trending
from src.config import get_db_url
from src.database.repository import Repository

DEFAULT_DAYS = [7, 30, 90]


def summarize(price_data: dict, days: int) -> dict:
    """Pure summary of a price_data dict (card_id -> [(date, price), ...]).

    Returns counts of cards, total observation points, and how many cards
    rank as gainers/losers per src.analytics.trending.
    """
    cards = len(price_data)
    points = sum(len(v) for v in price_data.values())

    scores = []
    for card_id, prices in price_data.items():
        score = compute_trending_score(card_id, prices, days)
        if score is not None:
            scores.append(score)

    gainers = rank_trending(scores, "up")
    losers = rank_trending(scores, "down")

    return {
        "days": days,
        "cards": cards,
        "points": points,
        "scored": len(scores),
        "gainers": len(gainers),
        "losers": len(losers),
    }


def _direct_source_count(repo: Repository, days: int) -> dict:
    """Direct count of price_observations for liga/manual patterns in the period."""
    cutoff = date.today() - timedelta(days=days)
    sql = text("""
        SELECT COUNT(*) AS rows, COUNT(DISTINCT external_id) AS distinct_external_ids
        FROM price_observations
        WHERE source IN ('liga', 'manual')
          AND (external_id LIKE 'liga\\_%' ESCAPE '\\' OR external_id LIKE 'manual\\_%' ESCAPE '\\')
          AND external_id NOT LIKE 'liga\\_catalog\\_%' ESCAPE '\\'
          AND observed_at >= :cutoff
    """)
    start = time.perf_counter()
    with repo.engine.connect() as conn:
        row = conn.execute(sql, {"cutoff": cutoff}).fetchone()
    elapsed = time.perf_counter() - start
    return {
        "rows": row[0] if row else 0,
        "distinct_external_ids": row[1] if row else 0,
        "elapsed": elapsed,
    }


def run_for_days(repo: Repository, days: int, user_id: int | None) -> None:
    print(f"\n{'=' * 65}")
    print(f"Period: {days}d")
    print(f"{'=' * 65}")

    start = time.perf_counter()
    price_data = repo.get_trending_price_data(days)
    elapsed = time.perf_counter() - start
    summary = summarize(price_data, days)
    print("1. get_trending_price_data (market mode):")
    print(
        f"   cards={summary['cards']} points={summary['points']} "
        f"scored={summary['scored']} elapsed={elapsed:.3f}s"
    )

    direct = _direct_source_count(repo, days)
    print("2. Direct liga/manual price_observations count:")
    print(
        f"   rows={direct['rows']} distinct_external_ids={direct['distinct_external_ids']} "
        f"elapsed={direct['elapsed']:.3f}s"
    )

    print("3. compute_trending_score + rank_trending over (1):")
    print(f"   gainers={summary['gainers']} losers={summary['losers']}")

    if user_id is not None:
        start = time.perf_counter()
        user_price_data = repo.get_trending_price_data_for_user(user_id, days)
        elapsed = time.perf_counter() - start
        user_summary = summarize(user_price_data, days)
        print(f"4. get_trending_price_data_for_user(user_id={user_id}):")
        print(
            f"   cards={user_summary['cards']} points={user_summary['points']} "
            f"scored={user_summary['scored']} elapsed={elapsed:.3f}s "
            f"gainers={user_summary['gainers']} losers={user_summary['losers']}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--days",
        type=int,
        nargs="+",
        default=DEFAULT_DAYS,
        help="Periods (days) to diagnose. Default: 7 30 90.",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        help="Optional user id to also run the collection-mode query for comparison.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    for d in args.days:
        if d <= 0:
            parser.error(f"--days values must be positive, got {d}")

    repo = Repository(get_db_url())

    for days in args.days:
        run_for_days(repo, days, args.user_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

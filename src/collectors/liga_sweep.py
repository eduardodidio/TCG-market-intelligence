"""Liga sweep orchestrator -- batch-processes the entire collection
through LigaMagic with configurable pacing for initial price population."""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import structlog

from src.config import get_db_url
from src.database.repository import Repository
from src.domain.models import HistoricalPrice, ScanFilter, ScanType

log = structlog.get_logger()


@dataclass
class LigaSweepResult:
    total_eligible: int
    total_processed: int
    prices_found: int
    prices_not_found: int
    errors: int
    batches_completed: int
    dry_run: bool


async def _fetch_liga_price(provider, card: dict) -> HistoricalPrice | None:
    """Fetch price for a single card via the Liga provider.

    Returns a HistoricalPrice observation or None if no price found.
    """
    card_name = card.get("name_en") or card.get("name_pt", "")
    card_id = card.get("card_id", 0)
    if not card_name:
        return None

    prices = await provider.search_card(card_name)
    normal = prices.get("normal", {})
    price: Decimal | None = normal.get("low") or normal.get("mid") or normal.get("high")
    if price is None:
        return None

    return HistoricalPrice(
        source="liga",
        external_id=f"liga_{card_id}",
        observed_at=date.today(),
        median_price=price,
        currency="BRL",
    )


async def run_liga_sweep(
    db_url: str | None = None,
    batch_size: int = 20,
    batch_pause: int = 60,
    delay: float = 5.0,
    max_age_days: int = 7,
    limit: int | None = None,
    dry_run: bool = False,
    set_filter: str | None = None,
) -> LigaSweepResult:
    """Sweep all eligible collection cards through LigaMagic.

    Args:
        db_url: Database connection string (defaults to TCG_DATABASE_URL).
        batch_size: Cards per batch before pausing.
        batch_pause: Seconds to pause between batches.
        delay: Seconds between individual card fetches.
        max_age_days: Skip cards with Liga price newer than N days.
        limit: Max total cards to process (None = all).
        dry_run: If True, return counts without fetching.
        set_filter: Only sweep cards from this set code.

    Returns:
        LigaSweepResult with aggregated counts.
    """
    db_url = db_url or get_db_url()
    repo = Repository(db_url)

    # Build scan filter
    scan_filter_obj = ScanFilter(
        scan_type=ScanType.LIGA_FULL,
        set_codes=[set_filter] if set_filter else None,
        limit=limit,
    )

    # Get eligible cards
    entries = repo.get_cards_for_liga_scan(
        scan_filter=scan_filter_obj,
        max_age_days=max_age_days,
    )
    total_eligible = len(entries)

    if dry_run:
        return LigaSweepResult(
            total_eligible=total_eligible,
            total_processed=0,
            prices_found=0,
            prices_not_found=0,
            errors=0,
            batches_completed=0,
            dry_run=True,
        )

    # Split into batches
    num_batches = max(1, math.ceil(total_eligible / batch_size))
    batches = [entries[i * batch_size : (i + 1) * batch_size] for i in range(num_batches)]
    # Remove empty trailing batch (if total_eligible is 0)
    batches = [b for b in batches if b]

    total_processed = 0
    prices_found = 0
    prices_not_found = 0
    errors = 0
    batches_completed = 0

    # Import LigaMagicProvider lazily to avoid Playwright import at module level
    from src.providers.liga.provider import LigaMagicProvider

    provider = LigaMagicProvider()
    try:
        await provider.open()

        for batch_idx, batch in enumerate(batches):
            batch_prices_found = 0

            for card in batch:
                card_name = card.get("name_en") or card.get("name_pt", "")
                try:
                    observation = await _fetch_liga_price(provider, card)

                    if observation is not None:
                        repo.insert_price_observations([observation])
                        prices_found += 1
                        batch_prices_found += 1
                    else:
                        prices_not_found += 1

                    total_processed += 1

                except Exception as exc:
                    errors += 1
                    total_processed += 1
                    log.warning(
                        "liga_sweep_card_error",
                        card_name=card_name,
                        error=str(exc),
                    )

                # Delay between cards (skip after last card in batch)
                if card is not batch[-1]:
                    await asyncio.sleep(delay)

            batches_completed += 1
            log.info(
                "liga_sweep_batch_complete",
                batch=f"{batches_completed}/{len(batches)}",
                prices_found=batch_prices_found,
                batch_size=len(batch),
            )

            # Pause between batches (skip after last batch)
            if batch_idx < len(batches) - 1:
                log.info(
                    "liga_sweep_batch_pause",
                    pause_seconds=batch_pause,
                )
                await asyncio.sleep(batch_pause)

    except KeyboardInterrupt:
        log.info(
            "liga_sweep_interrupted",
            total_processed=total_processed,
            prices_found=prices_found,
        )
    finally:
        await provider.close()

    return LigaSweepResult(
        total_eligible=total_eligible,
        total_processed=total_processed,
        prices_found=prices_found,
        prices_not_found=prices_not_found,
        errors=errors,
        batches_completed=batches_completed,
        dry_run=False,
    )

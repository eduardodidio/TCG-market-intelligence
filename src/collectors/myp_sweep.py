"""MYP sweep orchestrator -- batch-processes the entire collection
through MYP Cards with configurable pacing for price updates.

Replaces Liga sweep when LigaMagic is blocked by Cloudflare.
Uses curl_cffi (no browser needed, no Cloudflare issues).
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import structlog

from src.collection.converter import is_foil_entry as _is_foil
from src.config import get_db_url
from src.database.repository import Repository
from src.domain.models import HistoricalPrice, ScanFilter, ScanRun, ScanType

log = structlog.get_logger()


@dataclass
class MypSweepResult:
    total_eligible: int
    total_processed: int
    prices_found: int
    prices_not_found: int
    errors: int
    batches_completed: int
    dry_run: bool
    daily_snapshot_created: int = 0


def _clean_card_name(name: str) -> str:
    """Strip annotations that confuse MYP search."""
    import re

    name = re.sub(r"\s*\(#\d+\)", "", name)
    variant_re = r"\s*\((?:Borderless|Extended\s+Art|Showcase|Etched|Retro\s+Frame)\)"
    name = re.sub(variant_re, "", name, flags=re.IGNORECASE)
    return name.strip()


def _best_match(results: list, card_name: str, set_code: str | None, collector_number: str | None):
    """Find the best matching MYP search result for a collection card.

    Priority:
    1. Exact set_code + collector_number match
    2. Exact set_code match (any collector_number)
    3. Name starts with card_name (first result)
    """
    if not results:
        return None

    card_name_lower = card_name.lower().strip()

    # Priority 1: set_code + collector_number
    if set_code and collector_number:
        for r in results:
            if (r.set_code or "").lower() == set_code.lower() and (r.collector_number or "").lstrip(
                "0"
            ) == collector_number.lstrip("0"):
                return r

    # Priority 2: set_code match
    if set_code:
        for r in results:
            if (r.set_code or "").lower() == set_code.lower():
                return r

    # Priority 3: name starts with card_name
    for r in results:
        r_name = (r.name or "").lower()
        # MYP names often have "Name EN // Name EN" format
        r_base = r_name.split("//")[0].strip()
        if r_base.startswith(card_name_lower) or card_name_lower.startswith(r_base):
            return r

    # Fallback: first result
    return results[0] if results else None


async def _fetch_myp_price(provider, card: dict) -> HistoricalPrice | None:
    """Fetch price for a single card via MYP Cards.

    Returns a HistoricalPrice or None if no price found.
    Tries multiple search results if the best match returns 404.
    """
    from src.providers.myp.exceptions import NotFoundError

    card_name = card.get("name_en") or card.get("name_pt", "")
    card_id = card.get("card_id", 0)
    if not card_name:
        return None

    card_name = _clean_card_name(card_name)
    set_code = card.get("set_code")
    collector_number = card.get("collector_number")
    is_foil_card = _is_foil(card.get("extras"))

    # Search MYP
    results = await provider.search_card(card_name)
    if not results:
        log.debug("myp_sweep_no_results", card=card_name, card_id=card_id)
        return None

    # Sort: best match first, then try others on 404
    best = _best_match(results, card_name, set_code, collector_number)
    candidates = [best] if best else []
    for r in results:
        if r not in candidates:
            candidates.append(r)

    for candidate in candidates[:5]:  # Try up to 5 results
        try:
            price_data = await provider.fetch_current_price(candidate.external_id, candidate.slug)
        except NotFoundError:
            log.debug(
                "myp_sweep_404_skip",
                card=card_name,
                myp_id=candidate.external_id,
            )
            continue
        except Exception:
            continue

        if price_data is None or price_data.price is None:
            continue

        price = Decimal(str(price_data.price))
        suffix = "_foil" if is_foil_card else ""
        external_id = f"myp_{card_id}{suffix}"

        log.debug(
            "myp_sweep_price_found",
            card=card_name,
            price=str(price),
            myp_id=candidate.external_id,
        )
        return HistoricalPrice(
            source="myp",
            external_id=external_id,
            observed_at=date.today(),
            median_price=price,
            currency=price_data.currency or "BRL",
        )

    log.debug("myp_sweep_no_price", card=card_name, card_id=card_id)
    return None


async def run_myp_sweep(
    db_url: str | None = None,
    batch_size: int = 20,
    batch_pause: int = 30,
    delay: float = 1.5,
    max_age_days: int = 7,
    limit: int | None = None,
    dry_run: bool = False,
    set_filter: str | None = None,
    on_complete: Callable[[ScanRun, list[str]], None] | None = None,
    snapshot_after: bool = True,
) -> MypSweepResult:
    """Sweep all eligible collection cards through MYP Cards.

    Args:
        db_url: Database connection string (defaults to TCG_DATABASE_URL).
        batch_size: Cards per batch before pausing.
        batch_pause: Seconds to pause between batches.
        delay: Seconds between individual card fetches.
        max_age_days: Skip cards with MYP price newer than N days.
        limit: Max total cards to process (None = all).
        dry_run: If True, return counts without fetching.
        set_filter: Only sweep cards from this set code.
        on_complete: Callback fired with the processed external_ids.
        snapshot_after: When True (default), write today's global
            daily_snapshot after a sweep that processed >=1 card.
    """
    db_url = db_url or get_db_url()
    repo = Repository(db_url)

    # Reuse the Liga scan query (it returns the same card fields we need)
    scan_filter_obj = ScanFilter(
        scan_type=ScanType.LIGA_FULL,
        set_codes=[set_filter] if set_filter else None,
        limit=limit,
    )
    entries = repo.get_cards_for_liga_scan(
        scan_filter=scan_filter_obj,
        max_age_days=max_age_days,
    )
    total_eligible = len(entries)

    if dry_run:
        return MypSweepResult(
            total_eligible=total_eligible,
            total_processed=0,
            prices_found=0,
            prices_not_found=0,
            errors=0,
            batches_completed=0,
            dry_run=True,
        )

    num_batches = max(1, math.ceil(total_eligible / batch_size))
    batches = [entries[i * batch_size : (i + 1) * batch_size] for i in range(num_batches)]
    batches = [b for b in batches if b]

    total_processed = 0
    prices_found = 0
    prices_not_found = 0
    errors = 0
    batches_completed = 0
    processed_external_ids: list[str] = []

    from src.providers.myp.provider import MypCardsProvider, MypConfig

    config = MypConfig(delay_seconds=delay)
    provider = MypCardsProvider(config)

    try:
        for batch_idx, batch in enumerate(batches):
            batch_prices_found = 0

            for card in batch:
                card_name = card.get("name_en") or card.get("name_pt", "")
                try:
                    observation = await _fetch_myp_price(provider, card)

                    if observation is not None:
                        repo.insert_price_observations([observation])
                        prices_found += 1
                        batch_prices_found += 1
                        processed_external_ids.append(observation.external_id)
                    else:
                        prices_not_found += 1

                    total_processed += 1

                except Exception as exc:
                    errors += 1
                    total_processed += 1
                    log.warning(
                        "myp_sweep_card_error",
                        card_name=card_name,
                        error=str(exc),
                    )

                # Delay between cards
                if card is not batch[-1]:
                    await asyncio.sleep(delay)

            batches_completed += 1
            log.info(
                "myp_sweep_batch_complete",
                batch=f"{batches_completed}/{len(batches)}",
                prices_found=batch_prices_found,
                batch_size=len(batch),
            )

            if batch_idx < len(batches) - 1:
                log.info("myp_sweep_batch_pause", pause_seconds=batch_pause)
                await asyncio.sleep(batch_pause)

    except KeyboardInterrupt:
        log.info(
            "myp_sweep_interrupted",
            total_processed=total_processed,
            prices_found=prices_found,
        )
    finally:
        await provider.close()

    # Fire on_complete callback
    if on_complete is not None and processed_external_ids:
        scan_run = ScanRun(
            id=None,
            scan_type="myp_sweep",
            status="completed",
            cards_total=total_eligible,
            cards_processed=total_processed,
        )
        try:
            on_complete(scan_run, processed_external_ids)
        except Exception:
            log.exception("myp_sweep_on_complete_error")

    daily_snapshot_created = 0
    if snapshot_after and total_processed > 0:
        from src.collectors.price_snapshot import run_daily_snapshot

        try:
            daily_snapshot_created = run_daily_snapshot(repo)
            log.info("myp_sweep_daily_snapshot", created=daily_snapshot_created)
        except Exception as exc:
            log.warning("myp_sweep_daily_snapshot_failed", error=str(exc))

    return MypSweepResult(
        total_eligible=total_eligible,
        total_processed=total_processed,
        prices_found=prices_found,
        prices_not_found=prices_not_found,
        errors=errors,
        batches_completed=batches_completed,
        dry_run=False,
        daily_snapshot_created=daily_snapshot_created,
    )

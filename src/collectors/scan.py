"""Collection scan orchestrator -- runs filtered price scans with
tracking via scan_runs table."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

import structlog

from src.database.repository import Repository
from src.domain.events import ScanEvent
from src.domain.models import (
    HistoricalPrice,
    ScanFilter,
    ScanRun,
    ScanStatus,
    ScanType,
)
from src.events import scan_bus
from src.providers.liga.exceptions import (
    LigaError,
    LigaNotFoundError,
    LigaRateLimitError,
)
from src.providers.myp.exceptions import NotFoundError, RateLimitError
from src.providers.myp.provider import MypCardsProvider, MypConfig

log = structlog.get_logger()

MAX_REQUEUE_ATTEMPTS = 2

# Liga-specific defaults
LIGA_CONCURRENCY = 1
LIGA_DEFAULT_DELAY = 5.0
LIGA_REQUEUE_DELAY_MULTIPLIER = 6  # 5s * 6 = 30s cooldown


async def _fetch_price_liga(provider, entry: dict, card_id: int) -> HistoricalPrice | None:
    """Fetch price for a single card via the Liga provider.

    Uses provider.search_card(name) which returns a parsed price dict
    with structure: {"normal": {"low": Decimal|None, "mid": ..., "high": ...}, ...}
    """
    card_name = entry.get("name_en") or entry.get("name_pt", "")
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


async def run_scan(
    db_url: str = "sqlite:///tcg_market.db",
    scan_filter: ScanFilter | None = None,
    dry_run: bool = False,
    delay: float = 1.0,
    concurrency: int = 3,
    run_id: int | None = None,
    on_complete: Callable[[ScanRun, list[str]], None] | None = None,
    provider: MypCardsProvider | None = None,
    provider_name: str = "myp",
    max_age_days: int | None = None,
) -> ScanRun:
    """Run a collection price scan with optional filtering.

    Args:
        db_url: Database connection string.
        scan_filter: Filter criteria (defaults to full collection).
        dry_run: If True, create scan run and get cards but skip fetching.
        delay: Seconds between requests.
        concurrency: Max concurrent requests.
        run_id: Pre-created scan run ID (from API).
        on_complete: Hook called after scan finishes.
        provider: Provider instance; created internally if None (MYP only).
        provider_name: Which provider to use ("myp" or "liga").
        max_age_days: For Liga scans, skip cards scanned within N days.
    """
    is_liga = provider_name == "liga"

    # Force Liga-specific constraints
    if is_liga:
        concurrency = LIGA_CONCURRENCY
        if delay < LIGA_DEFAULT_DELAY:
            delay = LIGA_DEFAULT_DELAY

    scan_filter = scan_filter or ScanFilter()

    # Override scan_type for Liga if using default collection type
    if is_liga and scan_filter.scan_type in (ScanType.COLLECTION, ScanType.CUSTOM):
        scan_filter = ScanFilter(
            scan_type=(
                ScanType.LIGA_FULL
                if scan_filter.scan_type == ScanType.COLLECTION
                else ScanType.LIGA_PARTIAL
            ),
            set_codes=scan_filter.set_codes,
            format_name=scan_filter.format_name,
            rarities=scan_filter.rarities,
            card_ids=scan_filter.card_ids,
            collection_only=scan_filter.collection_only,
            limit=scan_filter.limit,
        )

    owns_provider = provider is None
    effective_delay = delay

    if provider is None and not is_liga:
        config = MypConfig(delay_seconds=delay)
        provider = MypCardsProvider(config)

    repo = Repository(db_url)
    today = date.today()

    # 1. Create scan run row (or reuse pre-created one from API)
    if run_id is None:
        run_id = repo.create_scan_run(scan_filter.scan_type.value, scan_filter.to_json())
    repo.update_scan_run(run_id, status=ScanStatus.RUNNING.value, started_at=datetime.now())

    try:
        # 2. Get cards matching filter
        if is_liga:
            entries = repo.get_cards_for_liga_scan(scan_filter, max_age_days=max_age_days)
        else:
            entries = repo.get_cards_for_scan(scan_filter)
        cards_total = len(entries)
        repo.update_scan_run(run_id, cards_total=cards_total)
        log.info(
            "scan_start",
            run_id=run_id,
            cards_total=cards_total,
            dry_run=dry_run,
            provider=provider_name,
        )

        # Publish scan_started event
        scan_bus.publish(
            ScanEvent(
                event_type="scan_started",
                scan_id=run_id,
                timestamp=datetime.now().isoformat(),
                cards_total=cards_total,
            )
        )

        if dry_run:
            repo.update_scan_run(
                run_id,
                status=ScanStatus.COMPLETED.value,
                cards_processed=0,
                finished_at=datetime.now(),
            )
            scan_bus.publish(
                ScanEvent(
                    event_type="scan_complete",
                    scan_id=run_id,
                    timestamp=datetime.now().isoformat(),
                    cards_total=cards_total,
                    cards_processed=0,
                )
            )
            return _build_scan_run(repo, run_id)

        # 3. Process entries with concurrency control
        cards_processed = 0
        cards_failed = 0
        observations_saved = 0
        error_messages: list[str] = []
        processed_external_ids: list[str] = []
        retry_queue: list[tuple[dict, int]] = []  # (entry, attempt_count)
        sem = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()

        def _persist_progress() -> None:
            """Persist current scan counters to the database so polling clients see updates."""
            repo.update_scan_run(
                run_id,
                cards_processed=cards_processed,
                cards_failed=cards_failed,
                observations_saved=observations_saved,
            )

        async def process_entry(entry: dict, index: int, attempt: int = 1) -> None:
            nonlocal cards_processed, cards_failed, observations_saved

            async with sem:
                external_id = entry.get("external_id", "")
                card_name = entry.get("name_en", "")
                card_id = entry.get("card_id", 0)

                # Identifier for logging/error messages
                entry_ident = external_id if not is_liga else (card_name or f"card_{card_id}")

                try:
                    if is_liga:
                        observation = await _fetch_price_liga(provider, entry, card_id)
                    else:
                        slug = entry.get("slug", "")
                        jsonld_price = await provider.fetch_current_price(external_id, slug)

                        if jsonld_price is None or jsonld_price.price is None:
                            observation = None
                        else:
                            observation = HistoricalPrice(
                                source="jsonld_snapshot",
                                external_id=external_id,
                                observed_at=today,
                                median_price=jsonld_price.price,
                                tcg_price=None,
                                currency=jsonld_price.currency,
                            )
                except (NotFoundError, LigaNotFoundError) as e:
                    async with lock:
                        cards_processed += 1
                        cards_failed += 1
                        error_messages.append(f"{entry_ident}: NotFoundError: {e}")
                        scan_bus.publish(
                            ScanEvent(
                                event_type="card_scanned",
                                scan_id=run_id,
                                timestamp=datetime.now().isoformat(),
                                external_id=external_id,
                                card_name=card_name,
                                price_found=False,
                                error=str(e),
                                cards_processed=cards_processed,
                                cards_total=cards_total,
                                cards_failed=cards_failed,
                                observations_saved=observations_saved,
                            )
                        )
                        _persist_progress()
                    log.warning(
                        "scan_not_found",
                        run_id=run_id,
                        external_id=entry_ident,
                        provider=provider_name,
                    )
                    return
                except (RateLimitError, LigaRateLimitError) as e:
                    if attempt < MAX_REQUEUE_ATTEMPTS:
                        async with lock:
                            retry_queue.append((entry, attempt + 1))
                        log.warning(
                            "scan_rate_limited_requeue",
                            run_id=run_id,
                            external_id=entry_ident,
                            attempt=attempt,
                            provider=provider_name,
                        )
                        return
                    async with lock:
                        cards_processed += 1
                        cards_failed += 1
                        error_messages.append(f"{entry_ident}: RateLimitError: {e}")
                        scan_bus.publish(
                            ScanEvent(
                                event_type="card_scanned",
                                scan_id=run_id,
                                timestamp=datetime.now().isoformat(),
                                external_id=external_id,
                                card_name=card_name,
                                price_found=False,
                                error=str(e),
                                cards_processed=cards_processed,
                                cards_total=cards_total,
                                cards_failed=cards_failed,
                                observations_saved=observations_saved,
                            )
                        )
                        _persist_progress()
                    log.warning(
                        "scan_rate_limited_exhausted",
                        run_id=run_id,
                        external_id=entry_ident,
                        provider=provider_name,
                    )
                    return
                except (LigaError, Exception) as e:
                    async with lock:
                        cards_processed += 1
                        cards_failed += 1
                        error_messages.append(f"{entry_ident}: {type(e).__name__}: {e}")
                        scan_bus.publish(
                            ScanEvent(
                                event_type="card_scanned",
                                scan_id=run_id,
                                timestamp=datetime.now().isoformat(),
                                external_id=external_id,
                                card_name=card_name,
                                price_found=False,
                                error=str(e),
                                cards_processed=cards_processed,
                                cards_total=cards_total,
                                cards_failed=cards_failed,
                                observations_saved=observations_saved,
                            )
                        )
                        _persist_progress()
                    log.warning(
                        "scan_fetch_error",
                        run_id=run_id,
                        external_id=entry_ident,
                        error=str(e),
                        provider=provider_name,
                    )
                    return

                if observation is None:
                    async with lock:
                        cards_processed += 1
                        scan_bus.publish(
                            ScanEvent(
                                event_type="card_scanned",
                                scan_id=run_id,
                                timestamp=datetime.now().isoformat(),
                                external_id=external_id,
                                card_name=card_name,
                                price_found=False,
                                cards_processed=cards_processed,
                                cards_total=cards_total,
                                cards_failed=cards_failed,
                                observations_saved=observations_saved,
                            )
                        )
                        _persist_progress()
                    log.debug(
                        "scan_skip_no_price",
                        external_id=entry_ident,
                        provider=provider_name,
                    )
                    return

                obs_external_id = observation.external_id
                inserted = repo.insert_price_observations([observation])
                async with lock:
                    cards_processed += 1
                    observations_saved += inserted
                    processed_external_ids.append(obs_external_id)
                    scan_bus.publish(
                        ScanEvent(
                            event_type="card_scanned",
                            scan_id=run_id,
                            timestamp=datetime.now().isoformat(),
                            external_id=obs_external_id,
                            card_name=card_name,
                            price_found=True,
                            price=observation.median_price,
                            currency=observation.currency,
                            cards_processed=cards_processed,
                            cards_total=cards_total,
                            cards_failed=cards_failed,
                            observations_saved=observations_saved,
                        )
                    )
                    _persist_progress()

                log.info(
                    "scan_stored",
                    run_id=run_id,
                    index=index,
                    external_id=obs_external_id,
                    price=str(observation.median_price),
                    provider=provider_name,
                )

        tasks = [process_entry(entry, i) for i, entry in enumerate(entries, 1)]
        await asyncio.gather(*tasks)

        # 3b. Retry pass for rate-limited cards
        if retry_queue:
            requeue_delay_multiplier = LIGA_REQUEUE_DELAY_MULTIPLIER if is_liga else 3
            log.info(
                "scan_retry_pass",
                run_id=run_id,
                retry_count=len(retry_queue),
                delay_multiplier=requeue_delay_multiplier,
            )
            await asyncio.sleep(effective_delay * requeue_delay_multiplier)
            retry_tasks = [
                process_entry(entry, i, attempt=attempt)
                for i, (entry, attempt) in enumerate(retry_queue, 1)
            ]
            retry_queue.clear()
            await asyncio.gather(*retry_tasks)

        # 4. Determine final status
        if cards_total == 0:
            status = ScanStatus.COMPLETED.value
        elif cards_failed > cards_total * 0.5:
            status = ScanStatus.FAILED.value
        else:
            status = ScanStatus.COMPLETED.value

        error_summary = json.dumps(error_messages) if error_messages else None

        repo.update_scan_run(
            run_id,
            status=status,
            cards_processed=cards_processed,
            cards_failed=cards_failed,
            observations_saved=observations_saved,
            error_summary=error_summary,
            finished_at=datetime.now(),
        )

        log.info(
            "scan_finished",
            run_id=run_id,
            status=status,
            cards_total=cards_total,
            cards_processed=cards_processed,
            cards_failed=cards_failed,
            observations_saved=observations_saved,
            provider=provider_name,
        )

        # Publish scan_complete event
        scan_bus.publish(
            ScanEvent(
                event_type="scan_complete",
                scan_id=run_id,
                timestamp=datetime.now().isoformat(),
                cards_processed=cards_processed,
                cards_total=cards_total,
                cards_failed=cards_failed,
                observations_saved=observations_saved,
                error=error_summary,
            )
        )

        scan_run = _build_scan_run(repo, run_id)

        # Invoke on_complete hook if provided
        if on_complete is not None:
            try:
                on_complete(scan_run, processed_external_ids)
            except Exception:
                log.exception("on_complete_hook_error", run_id=run_id)

        return scan_run

    except Exception as exc:
        repo.update_scan_run(
            run_id,
            status=ScanStatus.FAILED.value,
            finished_at=datetime.now(),
        )
        # Publish scan_complete event with error
        scan_bus.publish(
            ScanEvent(
                event_type="scan_complete",
                scan_id=run_id,
                timestamp=datetime.now().isoformat(),
                error=str(exc),
            )
        )

        # Capture in error logger
        from src.errors.logger import get_global_error_logger

        error_logger = get_global_error_logger()
        if error_logger:
            error_logger.capture(exc, extra={"scan_id": run_id, "context": "scan_loop"})

        raise
    finally:
        if owns_provider and provider is not None:
            await provider.close()
        # Delayed cleanup: give SSE clients time to receive the final event
        await asyncio.sleep(5)
        scan_bus.cleanup(run_id)


def _build_scan_run(repo: Repository, run_id: int) -> ScanRun:
    """Read the scan run row from DB and return a ScanRun domain object."""
    row = repo.get_scan_run(run_id)
    if row is None:
        raise ValueError(f"Scan run {run_id} not found")
    return ScanRun(
        id=row["id"],
        scan_type=row["scan_type"],
        filters_json=row["filters_json"],
        status=row["status"],
        cards_total=row["cards_total"],
        cards_processed=row["cards_processed"],
        cards_failed=row["cards_failed"],
        observations_saved=row["observations_saved"],
        error_summary=row["error_summary"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )

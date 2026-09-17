"""Reusable module for processing pending price update requests.

Extracted from the CLI ``process-price-requests`` command so that both
the CLI and the admin API endpoint can reuse the same logic.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Summary of a price request processing run."""

    total: int
    completed: int
    failed: int


async def process_pending_price_requests(
    db_url: str,
    limit: int = 50,
    delay: float = 2.0,
) -> ProcessingResult:
    """Process pending price update requests via LigaMagic.

    Returns a ``ProcessingResult`` with counts of completed and failed requests.

    Parameters
    ----------
    db_url:
        SQLAlchemy database URL.
    limit:
        Maximum number of pending requests to process in this run.
    delay:
        Seconds to wait between individual requests (rate limiting).
    """
    from src.collectors.liga_sweep import _fetch_liga_price
    from src.database.repository import Repository
    from src.providers.liga.exceptions import LigaError
    from src.providers.liga.provider import LigaMagicProvider

    repo = Repository(db_url=db_url)
    pending = repo.get_pending_price_requests(limit=limit)

    if not pending:
        return ProcessingResult(total=0, completed=0, failed=0)

    provider = LigaMagicProvider()
    completed = 0
    failed = 0

    try:
        await provider.initialize()

        for req in pending:
            card = repo.get_card_by_id(req.card_id)
            if not card:
                repo.update_price_request_status(
                    req.id, "failed", error_message="Card not found in database"
                )
                failed += 1
                continue

            card_name = card.name_en or card.name_pt
            if not card_name:
                repo.update_price_request_status(req.id, "failed", error_message="Card has no name")
                failed += 1
                continue

            # Mark as processing
            repo.update_price_request_status(req.id, "processing")

            try:
                card_dict = {
                    "card_id": card.id,
                    "name_en": card.name_en,
                    "name_pt": card.name_pt,
                    "collector_number": card.collector_number,
                    "set_code": card.set_code,
                }
                result = await _fetch_liga_price(provider, card_dict)

                if result is not None:
                    observation, _page_url = result
                    repo.insert_price_observations([observation])
                    price = observation.median_price
                    repo.update_price_request_status(req.id, "completed", result_price=price)
                    logger.info(
                        "Price request completed: card_id=%d (%s) -> R$ %s",
                        card.id,
                        card_name[:30],
                        price,
                    )
                    completed += 1
                else:
                    repo.update_price_request_status(
                        req.id, "completed", error_message="No price found on LigaMagic"
                    )
                    logger.info(
                        "Price request completed (no price): card_id=%d (%s)",
                        card.id,
                        card_name[:30],
                    )
                    completed += 1

            except LigaError as exc:
                repo.update_price_request_status(req.id, "failed", error_message=str(exc))
                logger.warning(
                    "Price request failed: card_id=%d (%s) -> %s",
                    card.id,
                    card_name[:30],
                    exc,
                )
                failed += 1
            except Exception as exc:
                msg = f"{type(exc).__name__}: {exc}"
                repo.update_price_request_status(req.id, "failed", error_message=msg)
                logger.warning(
                    "Price request failed: card_id=%d (%s) -> %s",
                    card.id,
                    card_name[:30],
                    msg,
                )
                failed += 1

            if delay > 0:
                await asyncio.sleep(delay)

    finally:
        await provider.close()

    return ProcessingResult(total=len(pending), completed=completed, failed=failed)

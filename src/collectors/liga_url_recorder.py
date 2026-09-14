"""Shared helper to persist the Liga page URL alongside a price observation."""

from __future__ import annotations

import structlog

from src.providers.liga.urls import is_valid_liga_card_url

log = structlog.get_logger()


def record_liga_url(repo, external_id: str, page_url: str | None) -> bool:
    """Persist the Liga page URL for a price external_id. Never raises.

    Returns True when the URL was stored, False when skipped (invalid/missing
    URL) or when the upsert failed.
    """
    if not is_valid_liga_card_url(page_url):
        return False

    try:
        repo.upsert_liga_card_url(external_id, page_url)
        return True
    except Exception as exc:
        log.warning("liga_url_record_failed", external_id=external_id, error=str(exc))
        return False

"""Tests for the `push-prices` CLI command.

`push-prices` pushes price observations to a *remote* DB over HTTP, so it must
NOT record the Liga page URL into the *local* `liga_card_urls` table — the URL
and the price would land in different databases and never coexist, breaking the
"link matches the price shown" guarantee. URL recording is owned by the
direct-to-Neon writers (liga-sweep, refresh-liga, scan). See F124 / ADR 0012.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cli.main import _push_prices_async

_LIGA_PAGE_URL = "https://www.ligamagic.com.br/?view=cards/card&card=x&show=1"


def _entry(card_id: int, name_en: str = "Lightning Bolt") -> dict:
    return {
        "card_id": card_id,
        "name_en": name_en,
        "name_pt": None,
        "extras": None,
    }


@pytest.mark.asyncio
async def test_push_prices_does_not_record_liga_url():
    """Even with a valid page_url and a real price, push-prices never writes
    the local liga_card_urls table."""
    mock_repo = MagicMock()
    mock_repo.get_cards_for_liga_scan.return_value = [_entry(1)]

    mock_provider = AsyncMock()
    mock_provider.open = AsyncMock()
    mock_provider.close = AsyncMock()
    mock_provider.search_card = AsyncMock(
        return_value={
            "normal": {"low": Decimal("5.00"), "mid": None, "high": None},
            "page_url": _LIGA_PAGE_URL,
        }
    )

    with (
        patch("src.database.repository.Repository", return_value=mock_repo),
        patch("src.providers.liga.provider.LigaMagicProvider", return_value=mock_provider),
    ):
        await _push_prices_async(
            db="sqlite:///:memory:",
            remote="https://example.com",
            api_key=None,
            delay=0,
            limit=None,
            dry_run=True,
            max_age_days=None,
        )

    mock_repo.upsert_liga_card_url.assert_not_called()


@pytest.mark.asyncio
async def test_push_prices_no_price_skips_url_recording():
    mock_repo = MagicMock()
    mock_repo.get_cards_for_liga_scan.return_value = [_entry(1)]

    mock_provider = AsyncMock()
    mock_provider.open = AsyncMock()
    mock_provider.close = AsyncMock()
    mock_provider.search_card = AsyncMock(
        return_value={
            "normal": {"low": None, "mid": None, "high": None},
            "page_url": _LIGA_PAGE_URL,
        }
    )

    with (
        patch("src.database.repository.Repository", return_value=mock_repo),
        patch("src.providers.liga.provider.LigaMagicProvider", return_value=mock_provider),
    ):
        await _push_prices_async(
            db="sqlite:///:memory:",
            remote="https://example.com",
            api_key=None,
            delay=0,
            limit=None,
            dry_run=True,
            max_age_days=None,
        )

    mock_repo.upsert_liga_card_url.assert_not_called()

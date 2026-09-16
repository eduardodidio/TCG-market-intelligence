"""Tests for the Liga sweep orchestrator."""

from __future__ import annotations

import math
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.collectors.liga_sweep import (
    LigaSweepResult,
    _clean_card_name,
    _fetch_liga_price,
    run_liga_sweep,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _make_card(card_id: int, name_en: str = "Card", name_pt: str = "Carta") -> dict:
    return {
        "entry_id": card_id,
        "card_id": card_id,
        "name_en": name_en,
        "name_pt": name_pt,
        "set_code": "DMU",
        "collector_number": str(card_id),
    }


def _make_cards(n: int) -> list[dict]:
    return [_make_card(i, f"Card {i}", f"Carta {i}") for i in range(1, n + 1)]


def _mock_provider_search(prices_map: dict | None = None):
    """Create a mock provider whose search_card returns prices from a map.

    prices_map: {card_name: Decimal|None}. If None, all cards return mid=1.50.
    """
    provider = AsyncMock()
    provider.open = AsyncMock()
    provider.close = AsyncMock()

    async def _search(name, **kwargs):
        if prices_map is not None:
            price = prices_map.get(name)
        else:
            price = Decimal("1.50")
        return {
            "normal": {"low": None, "mid": price, "high": None},
            "page_url": "https://www.ligamagic.com.br/?view=cards/card&card=x&show=1",
        }

    provider.search_card = AsyncMock(side_effect=_search)
    return provider


# ── Unit: _fetch_liga_price ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_liga_price_found():
    provider = _mock_provider_search()
    card = _make_card(42, "Lightning Bolt")
    result = await _fetch_liga_price(provider, card)

    assert result is not None
    observation, page_url = result
    assert observation.source == "liga"
    assert observation.external_id == "liga_42"
    assert observation.median_price == Decimal("1.50")
    assert observation.currency == "BRL"
    assert observation.observed_at == date.today()
    assert page_url == "https://www.ligamagic.com.br/?view=cards/card&card=x&show=1"


@pytest.mark.asyncio
async def test_fetch_liga_price_not_found():
    provider = _mock_provider_search({"Lightning Bolt": None})
    card = _make_card(42, "Lightning Bolt")
    result = await _fetch_liga_price(provider, card)

    assert result is None


@pytest.mark.asyncio
async def test_fetch_liga_price_no_name():
    provider = _mock_provider_search()
    card = _make_card(42, "", "")
    result = await _fetch_liga_price(provider, card)

    assert result is None


@pytest.mark.asyncio
async def test_fetch_liga_price_uses_name_pt_fallback():
    """When name_en is empty, should fall back to name_pt."""
    provider = _mock_provider_search({"Raio": Decimal("3.00")})
    card = {"entry_id": 1, "card_id": 1, "name_en": "", "name_pt": "Raio"}
    result = await _fetch_liga_price(provider, card)

    assert result is not None
    observation, _page_url = result
    assert observation.median_price == Decimal("3.00")
    provider.search_card.assert_awaited_once_with("Raio", collector_number=None, set_code=None)


@pytest.mark.asyncio
async def test_fetch_liga_price_prefers_mid_over_low():
    """Sweep uses 'mid' (mercado) per CLAUDE.md, not 'low' (menor anuncio)."""
    provider = AsyncMock()

    async def _search(name, **kwargs):
        return {"normal": {"low": Decimal("1.00"), "mid": Decimal("2.00"), "high": Decimal("3.00")}}

    provider.search_card = AsyncMock(side_effect=_search)
    card = _make_card(1, "Card")
    result = await _fetch_liga_price(provider, card)

    observation, _page_url = result
    assert observation.median_price == Decimal("2.00")


@pytest.mark.asyncio
async def test_fetch_liga_price_fallback_mid_when_no_low():
    provider = AsyncMock()

    async def _search(name, **kwargs):
        return {"normal": {"low": None, "mid": Decimal("2.00"), "high": Decimal("3.00")}}

    provider.search_card = AsyncMock(side_effect=_search)
    card = _make_card(1, "Card")
    result = await _fetch_liga_price(provider, card)

    observation, _page_url = result
    assert observation.median_price == Decimal("2.00")


@pytest.mark.asyncio
async def test_fetch_liga_price_fallback_high_when_no_low_no_mid():
    provider = AsyncMock()

    async def _search(name, **kwargs):
        return {"normal": {"low": None, "mid": None, "high": Decimal("3.00")}}

    provider.search_card = AsyncMock(side_effect=_search)
    card = _make_card(1, "Card")
    result = await _fetch_liga_price(provider, card)

    observation, _page_url = result
    assert observation.median_price == Decimal("3.00")


@pytest.mark.asyncio
async def test_fetch_liga_price_falls_back_to_low():
    provider = AsyncMock()

    async def _search(name, **kwargs):
        return {"normal": {"low": Decimal("1.00"), "mid": None, "high": None}}

    provider.search_card = AsyncMock(side_effect=_search)
    card = _make_card(1, "Card")
    result = await _fetch_liga_price(provider, card)

    observation, _page_url = result
    assert observation.median_price == Decimal("1.00")


@pytest.mark.asyncio
async def test_fetch_liga_price_falls_back_to_high():
    provider = AsyncMock()

    async def _search(name, **kwargs):
        return {"normal": {"low": None, "mid": None, "high": Decimal("5.00")}}

    provider.search_card = AsyncMock(side_effect=_search)
    card = _make_card(1, "Card")
    result = await _fetch_liga_price(provider, card)

    observation, _page_url = result
    assert observation.median_price == Decimal("5.00")


# ── Unit: batch splitting ────────────────────────────────────────────


def test_batch_splitting_20_cards_1_batch():
    cards = _make_cards(20)
    batch_size = 20
    num_batches = max(1, math.ceil(len(cards) / batch_size))
    batches = [cards[i * batch_size : (i + 1) * batch_size] for i in range(num_batches)]
    batches = [b for b in batches if b]

    assert len(batches) == 1
    assert len(batches[0]) == 20


def test_batch_splitting_50_cards_3_batches():
    cards = _make_cards(50)
    batch_size = 20
    num_batches = max(1, math.ceil(len(cards) / batch_size))
    batches = [cards[i * batch_size : (i + 1) * batch_size] for i in range(num_batches)]
    batches = [b for b in batches if b]

    assert len(batches) == 3
    assert len(batches[0]) == 20
    assert len(batches[1]) == 20
    assert len(batches[2]) == 10


def test_batch_splitting_0_cards():
    cards = []
    batch_size = 20
    num_batches = max(1, math.ceil(len(cards) / batch_size)) if cards else 0
    batches = [cards[i * batch_size : (i + 1) * batch_size] for i in range(num_batches)]
    batches = [b for b in batches if b]

    assert len(batches) == 0


# ── Unit: dry_run ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dry_run_returns_counts_without_fetching():
    cards = _make_cards(15)
    mock_repo = MagicMock()
    mock_repo.get_cards_for_liga_scan.return_value = cards

    with (
        patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
        patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
    ):
        result = await run_liga_sweep(
            db_url="sqlite:///:memory:",
            dry_run=True,
        )

    assert result.dry_run is True
    assert result.total_eligible == 15
    assert result.total_processed == 0
    assert result.prices_found == 0
    assert result.prices_not_found == 0
    assert result.errors == 0
    assert result.batches_completed == 0


# ── Unit: LigaSweepResult ───────────────────────────────────────────


def test_liga_sweep_result_dataclass():
    result = LigaSweepResult(
        total_eligible=100,
        total_processed=80,
        prices_found=60,
        prices_not_found=15,
        errors=5,
        batches_completed=4,
        dry_run=False,
    )
    assert result.total_eligible == 100
    assert result.total_processed == 80
    assert result.prices_found == 60
    assert result.prices_not_found == 15
    assert result.errors == 5
    assert result.batches_completed == 4
    assert result.dry_run is False


# ── Unit: set_filter passed through ─────────────────────────────────


@pytest.mark.asyncio
async def test_set_filter_passed_to_repo():
    mock_repo = MagicMock()
    mock_repo.get_cards_for_liga_scan.return_value = []

    with (
        patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
        patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
    ):
        await run_liga_sweep(
            db_url="sqlite:///:memory:",
            set_filter="DMU",
            dry_run=True,
        )

    call_args = mock_repo.get_cards_for_liga_scan.call_args
    scan_filter = (
        call_args.kwargs.get("scan_filter") or call_args[1].get("scan_filter") or call_args[0][0]
    )
    assert scan_filter.set_codes == ["DMU"]


@pytest.mark.asyncio
async def test_max_age_days_passed_to_repo():
    mock_repo = MagicMock()
    mock_repo.get_cards_for_liga_scan.return_value = []

    with (
        patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
        patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
    ):
        await run_liga_sweep(
            db_url="sqlite:///:memory:",
            max_age_days=14,
            dry_run=True,
        )

    call_args = mock_repo.get_cards_for_liga_scan.call_args
    assert call_args.kwargs.get("max_age_days") == 14


@pytest.mark.asyncio
async def test_limit_passed_to_scan_filter():
    mock_repo = MagicMock()
    mock_repo.get_cards_for_liga_scan.return_value = []

    with (
        patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
        patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
    ):
        await run_liga_sweep(
            db_url="sqlite:///:memory:",
            limit=50,
            dry_run=True,
        )

    call_args = mock_repo.get_cards_for_liga_scan.call_args
    scan_filter = (
        call_args.kwargs.get("scan_filter") or call_args[1].get("scan_filter") or call_args[0][0]
    )
    assert scan_filter.limit == 50


# ── Unit: graceful interruption ──────────────────────────────────────


@pytest.mark.asyncio
async def test_graceful_interruption_returns_partial_results():
    cards = _make_cards(5)
    mock_repo = MagicMock()
    mock_repo.get_cards_for_liga_scan.return_value = cards
    mock_repo.insert_price_observations.return_value = 1

    call_count = 0

    async def _search_with_interrupt(name, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count >= 3:
            raise KeyboardInterrupt()
        return {"normal": {"low": None, "mid": Decimal("1.50"), "high": None}}

    mock_provider = AsyncMock()
    mock_provider.open = AsyncMock()
    mock_provider.close = AsyncMock()
    mock_provider.search_card = AsyncMock(side_effect=_search_with_interrupt)

    with (
        patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
        patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        patch("src.providers.liga.provider.LigaMagicProvider", return_value=mock_provider),
    ):
        result = await run_liga_sweep(
            db_url="sqlite:///:memory:",
            batch_size=20,
            delay=0,
        )

    # Should have partial results
    assert result.total_eligible == 5
    assert result.total_processed == 2  # only 2 succeeded before interrupt
    assert result.prices_found == 2
    assert result.dry_run is False
    # Provider was closed even after interrupt
    mock_provider.close.assert_awaited_once()


# ── Integration: mock provider, 5 cards, batch_size=2 ────────────────


@pytest.mark.asyncio
async def test_integration_5_cards_batch_2():
    """5 cards with batch_size=2 should produce 3 batches (2+2+1)."""
    cards = _make_cards(5)
    mock_repo = MagicMock()
    mock_repo.get_cards_for_liga_scan.return_value = cards
    mock_repo.insert_price_observations.return_value = 1

    prices_map = {
        "Card 1": Decimal("1.00"),
        "Card 2": Decimal("2.00"),
        "Card 3": None,  # not found
        "Card 4": Decimal("4.00"),
        "Card 5": Decimal("5.00"),
    }
    mock_provider = _mock_provider_search(prices_map)

    with (
        patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
        patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        patch("src.providers.liga.provider.LigaMagicProvider", return_value=mock_provider),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await run_liga_sweep(
            db_url="sqlite:///:memory:",
            batch_size=2,
            batch_pause=10,
            delay=1.0,
        )

    assert result.total_eligible == 5
    assert result.total_processed == 5
    assert result.prices_found == 4
    assert result.prices_not_found == 1
    assert result.errors == 0
    assert result.batches_completed == 3
    assert result.dry_run is False

    # Verify observations were saved for found prices
    assert mock_repo.insert_price_observations.call_count == 4

    # Verify the Liga page URL was recorded alongside each found price
    assert mock_repo.upsert_liga_card_url.call_count == 4
    recorded_ids = {call.args[0] for call in mock_repo.upsert_liga_card_url.call_args_list}
    assert recorded_ids == {"liga_1", "liga_2", "liga_4", "liga_5"}


@pytest.mark.asyncio
async def test_foil_card_records_url_with_foil_suffix():
    card = _make_card(7, "Foil Card")
    card["extras"] = "foil"
    mock_repo = MagicMock()
    mock_repo.get_cards_for_liga_scan.return_value = [card]
    mock_repo.insert_price_observations.return_value = 1

    mock_provider = AsyncMock()
    mock_provider.open = AsyncMock()
    mock_provider.close = AsyncMock()

    async def _search(name, **kwargs):
        return {
            "normal": {"low": None, "mid": None, "high": None},
            "foil": {"low": None, "mid": Decimal("9.00"), "high": None},
            "page_url": "https://www.ligamagic.com.br/?view=cards/card&card=x&show=1",
        }

    mock_provider.search_card = AsyncMock(side_effect=_search)

    with (
        patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
        patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        patch("src.providers.liga.provider.LigaMagicProvider", return_value=mock_provider),
        patch("src.collectors.liga_sweep._is_foil", return_value=True),
    ):
        result = await run_liga_sweep(db_url="sqlite:///:memory:", delay=0)

    assert result.prices_found == 1
    mock_repo.upsert_liga_card_url.assert_called_once_with(
        "liga_7_foil", "https://www.ligamagic.com.br/?view=cards/card&card=x&show=1"
    )


@pytest.mark.asyncio
async def test_no_price_found_does_not_record_url():
    cards = _make_cards(1)
    mock_repo = MagicMock()
    mock_repo.get_cards_for_liga_scan.return_value = cards

    mock_provider = _mock_provider_search({"Card 1": None})

    with (
        patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
        patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        patch("src.providers.liga.provider.LigaMagicProvider", return_value=mock_provider),
    ):
        result = await run_liga_sweep(db_url="sqlite:///:memory:", delay=0)

    assert result.prices_not_found == 1
    mock_repo.upsert_liga_card_url.assert_not_called()


@pytest.mark.asyncio
async def test_provider_error_does_not_record_url():
    cards = _make_cards(1)
    mock_repo = MagicMock()
    mock_repo.get_cards_for_liga_scan.return_value = cards

    mock_provider = AsyncMock()
    mock_provider.open = AsyncMock()
    mock_provider.close = AsyncMock()
    mock_provider.search_card = AsyncMock(side_effect=RuntimeError("boom"))

    with (
        patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
        patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        patch("src.providers.liga.provider.LigaMagicProvider", return_value=mock_provider),
    ):
        result = await run_liga_sweep(db_url="sqlite:///:memory:", delay=0)

    assert result.errors == 1
    mock_repo.upsert_liga_card_url.assert_not_called()


@pytest.mark.asyncio
async def test_integration_errors_counted():
    """Cards that raise exceptions during fetch should be counted as errors."""
    cards = _make_cards(3)
    mock_repo = MagicMock()
    mock_repo.get_cards_for_liga_scan.return_value = cards
    mock_repo.insert_price_observations.return_value = 1

    call_count = 0

    async def _search_with_error(name, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("Connection failed")
        return {"normal": {"low": None, "mid": Decimal("1.50"), "high": None}}

    mock_provider = AsyncMock()
    mock_provider.open = AsyncMock()
    mock_provider.close = AsyncMock()
    mock_provider.search_card = AsyncMock(side_effect=_search_with_error)

    with (
        patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
        patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        patch("src.providers.liga.provider.LigaMagicProvider", return_value=mock_provider),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await run_liga_sweep(
            db_url="sqlite:///:memory:",
            batch_size=20,
            delay=0,
        )

    assert result.total_processed == 3
    assert result.prices_found == 2
    assert result.errors == 1


@pytest.mark.asyncio
async def test_no_cards_eligible():
    mock_repo = MagicMock()
    mock_repo.get_cards_for_liga_scan.return_value = []

    with (
        patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
        patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        patch("src.providers.liga.provider.LigaMagicProvider") as mock_cls,
    ):
        mock_provider = AsyncMock()
        mock_provider.open = AsyncMock()
        mock_provider.close = AsyncMock()
        mock_cls.return_value = mock_provider

        result = await run_liga_sweep(
            db_url="sqlite:///:memory:",
            delay=0,
        )

    assert result.total_eligible == 0
    assert result.total_processed == 0
    assert result.batches_completed == 0


@pytest.mark.asyncio
async def test_default_db_url_from_config():
    """When db_url is None, should use get_db_url()."""
    mock_repo = MagicMock()
    mock_repo.get_cards_for_liga_scan.return_value = []

    with (
        patch("src.collectors.liga_sweep.Repository", return_value=mock_repo) as mock_repo_cls,
        patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///custom.db"),
        patch("src.providers.liga.provider.LigaMagicProvider") as mock_cls,
    ):
        mock_provider = AsyncMock()
        mock_provider.open = AsyncMock()
        mock_provider.close = AsyncMock()
        mock_cls.return_value = mock_provider

        await run_liga_sweep(db_url=None, dry_run=True)

    mock_repo_cls.assert_called_once_with("sqlite:///custom.db")


# ── Unit: _clean_card_name ──────────────────────────────────────────


@pytest.mark.parametrize(
    "input_name, expected",
    [
        ("Arcane Signet (#333)", "Arcane Signet"),
        ("Sol Ring (#357)", "Sol Ring"),
        ("Command Tower (#485)", "Command Tower"),
        ("Lightning Bolt", "Lightning Bolt"),
        ("Card Name", "Card Name"),
        ("", ""),
        ("Card (#1) Other", "Card Other"),
    ],
)
def test_clean_card_name(input_name, expected):
    assert _clean_card_name(input_name) == expected


# ── Unit: edition mismatch skips price ──────────────────────────────


@pytest.mark.asyncio
async def test_fetch_liga_price_skips_on_edition_mismatch():
    """When Liga has edition options but none match, skip the price."""
    provider = AsyncMock()

    async def _search(name, **kwargs):
        return {
            "normal": {
                "low": Decimal("500.00"),
                "mid": Decimal("800.00"),
                "high": Decimal("1000.00"),
            },
            "edition_matched": False,
            "page_url": "https://www.ligamagic.com.br/?view=cards/card&card=x&show=1",
        }

    provider.search_card = AsyncMock(side_effect=_search)
    card = _make_card(503, "Arcane Signet")
    card["collector_number"] = "333"
    result = await _fetch_liga_price(provider, card)

    assert result is None


@pytest.mark.asyncio
async def test_fetch_liga_price_stores_when_edition_matched():
    """When Liga edition selection succeeds, store the price normally."""
    provider = AsyncMock()

    async def _search(name, **kwargs):
        return {
            "normal": {"low": Decimal("5.00"), "mid": Decimal("8.00"), "high": Decimal("12.00")},
            "edition_matched": True,
            "page_url": "https://www.ligamagic.com.br/?view=cards/card&card=x&show=1",
        }

    provider.search_card = AsyncMock(side_effect=_search)
    card = _make_card(503, "Arcane Signet")
    card["collector_number"] = "333"
    result = await _fetch_liga_price(provider, card)

    assert result is not None
    observation, _ = result
    assert observation.median_price == Decimal("8.00")


@pytest.mark.asyncio
async def test_fetch_liga_price_stores_when_no_edition_flag():
    """Backward compat: if edition_matched is absent, store normally."""
    provider = _mock_provider_search()
    card = _make_card(42, "Lightning Bolt")
    result = await _fetch_liga_price(provider, card)

    assert result is not None


@pytest.mark.asyncio
async def test_fetch_liga_price_strips_collector_number_annotation():
    """Card names with (#xxx) annotations should be cleaned before search."""
    provider = _mock_provider_search({"Arcane Signet": Decimal("8.00")})
    card = _make_card(503, "Arcane Signet (#333)")
    result = await _fetch_liga_price(provider, card)

    assert result is not None
    observation, _ = result
    assert observation.median_price == Decimal("8.00")
    # Verify the cleaned name was used in the search
    provider.search_card.assert_awaited_once_with(
        "Arcane Signet", collector_number="503", set_code="DMU"
    )

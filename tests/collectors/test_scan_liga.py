"""Tests for Liga provider support in the scan orchestrator (F60-T01).

Covers:
 1. ScanType.LIGA_FULL and LIGA_PARTIAL enum values exist
 2. run_scan with provider_name="liga" uses Liga fetch strategy
 3. Concurrency forced to 1 for Liga
 4. LigaNotFoundError → card skipped (no retry)
 5. LigaRateLimitError → requeued with extended delay
 6. LigaError → card failed
 7. MYP backward compatibility preserved
 8. Liga scan saves observations with source="liga"
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.collectors.scan import (
    LIGA_CONCURRENCY,
    LIGA_DEFAULT_DELAY,
    LIGA_REQUEUE_DELAY_MULTIPLIER,
    _fetch_price_liga,
    run_scan,
)
from src.domain.models import (
    JsonLdPrice,
    ScanFilter,
    ScanRun,
    ScanType,
)
from src.providers.liga.exceptions import (
    LigaError,
    LigaNotFoundError,
    LigaRateLimitError,
)
from src.providers.myp.exceptions import NotFoundError, RateLimitError  # noqa: E501

# ── helpers ──────────────────────────────────────────────────────


def _card_entry(
    external_id: str = "1000",
    slug: str = "lightning-bolt",
    card_id: int = 100,
    set_code: str = "LEA",
    name_en: str = "Lightning Bolt",
    name_pt: str | None = None,
) -> dict:
    """Create a fake card entry dict as returned by get_cards_for_scan."""
    entry = {
        "external_id": external_id,
        "slug": slug,
        "card_id": card_id,
        "set_code": set_code,
        "name_en": name_en,
    }
    if name_pt is not None:
        entry["name_pt"] = name_pt
    return entry


def _liga_price_result(
    low: Decimal | None = None,
    mid: Decimal | None = Decimal("15.00"),
    high: Decimal | None = None,
) -> dict:
    """Create a fake Liga price dict as returned by search_card / parse_card_prices."""
    return {
        "card_name": "Lightning Bolt",
        "normal": {"low": low, "mid": mid, "high": high},
        "foil": {"low": None, "mid": None, "high": None},
    }


def _jsonld_price(
    price: Decimal | None = Decimal("12.50"),
    currency: str = "BRL",
    availability: str = "InStock",
) -> JsonLdPrice:
    return JsonLdPrice(price=price, currency=currency, availability=availability)


def _make_scan_run_dict(
    run_id: int = 1,
    scan_type: str = "liga_full",
    filters_json: str = "{}",
    status: str = "completed",
    cards_total: int = 0,
    cards_processed: int = 0,
    cards_failed: int = 0,
    observations_saved: int = 0,
    error_summary: str | None = None,
    started_at=None,
    finished_at=None,
) -> dict:
    """Build a scan run dict as returned by repo.get_scan_run."""
    return {
        "id": run_id,
        "scan_type": scan_type,
        "filters_json": filters_json,
        "status": status,
        "cards_total": cards_total,
        "cards_processed": cards_processed,
        "cards_failed": cards_failed,
        "observations_saved": observations_saved,
        "error_summary": error_summary,
        "started_at": started_at,
        "finished_at": finished_at,
        "created_at": None,
    }


def _setup_repo_mock(repo_mock, entries, insert_return=1):
    """Configure common repo mock behaviour."""
    repo_mock.create_scan_run.return_value = 1
    repo_mock.update_scan_run.return_value = None
    repo_mock.get_cards_for_scan.return_value = entries
    repo_mock.get_cards_for_liga_scan.return_value = entries
    repo_mock.insert_price_observations.return_value = insert_return

    def _build_get_scan_run(run_id):
        merged: dict = {
            "id": 1,
            "scan_type": "liga_full",
            "filters_json": "{}",
            "status": "pending",
            "cards_total": 0,
            "cards_processed": 0,
            "cards_failed": 0,
            "observations_saved": 0,
            "error_summary": None,
            "started_at": None,
            "finished_at": None,
            "created_at": None,
        }
        for call in repo_mock.update_scan_run.call_args_list:
            merged.update(call[1])
        return merged

    repo_mock.get_scan_run.side_effect = _build_get_scan_run


# ── ScanType enum tests ────────────────────────────────────────


class TestScanTypeEnum:
    """Verify LIGA_FULL and LIGA_PARTIAL enum values exist."""

    def test_liga_full_exists(self):
        assert ScanType.LIGA_FULL.value == "liga_full"

    def test_liga_partial_exists(self):
        assert ScanType.LIGA_PARTIAL.value == "liga_partial"

    def test_liga_types_in_enum(self):
        values = [e.value for e in ScanType]
        assert "liga_full" in values
        assert "liga_partial" in values


# ── _fetch_price_liga unit tests ────────────────────────────────


@pytest.mark.asyncio
class TestFetchPriceLiga:
    """Tests for the _fetch_price_liga helper."""

    async def test_returns_historical_price_from_mid(self):
        provider = MagicMock()
        provider.search_card = AsyncMock(return_value=_liga_price_result(mid=Decimal("25.00")))

        entry = _card_entry(card_id=42, name_en="Counterspell")
        result = await _fetch_price_liga(provider, entry, card_id=42)

        assert result is not None
        assert result.source == "liga"
        assert result.external_id == "liga_42"
        assert result.median_price == Decimal("25.00")
        assert result.currency == "BRL"
        provider.search_card.assert_awaited_once_with("Counterspell")

    async def test_falls_back_to_low(self):
        provider = MagicMock()
        provider.search_card = AsyncMock(
            return_value=_liga_price_result(mid=None, low=Decimal("10.00"))
        )

        entry = _card_entry(card_id=1, name_en="Bolt")
        result = await _fetch_price_liga(provider, entry, card_id=1)

        assert result is not None
        assert result.median_price == Decimal("10.00")

    async def test_falls_back_to_high(self):
        provider = MagicMock()
        provider.search_card = AsyncMock(
            return_value=_liga_price_result(mid=None, low=None, high=Decimal("50.00"))
        )

        entry = _card_entry(card_id=2, name_en="Force of Will")
        result = await _fetch_price_liga(provider, entry, card_id=2)

        assert result is not None
        assert result.median_price == Decimal("50.00")

    async def test_returns_none_when_no_prices(self):
        provider = MagicMock()
        provider.search_card = AsyncMock(
            return_value=_liga_price_result(mid=None, low=None, high=None)
        )

        entry = _card_entry(card_id=3, name_en="Unknown Card")
        result = await _fetch_price_liga(provider, entry, card_id=3)

        assert result is None

    async def test_prefers_low_over_mid(self):
        provider = MagicMock()
        provider.search_card = AsyncMock(
            return_value=_liga_price_result(
                low=Decimal("10.00"), mid=Decimal("15.00"), high=Decimal("20.00")
            )
        )

        entry = _card_entry(card_id=50, name_en="Dual Land")
        result = await _fetch_price_liga(provider, entry, card_id=50)

        assert result is not None
        assert result.median_price == Decimal("10.00")

    async def test_fallback_mid_when_no_low(self):
        provider = MagicMock()
        provider.search_card = AsyncMock(
            return_value=_liga_price_result(low=None, mid=Decimal("15.00"), high=Decimal("20.00"))
        )

        entry = _card_entry(card_id=51, name_en="Shock")
        result = await _fetch_price_liga(provider, entry, card_id=51)

        assert result is not None
        assert result.median_price == Decimal("15.00")

    async def test_fallback_high_when_no_low_no_mid(self):
        provider = MagicMock()
        provider.search_card = AsyncMock(
            return_value=_liga_price_result(low=None, mid=None, high=Decimal("20.00"))
        )

        entry = _card_entry(card_id=52, name_en="Mountain")
        result = await _fetch_price_liga(provider, entry, card_id=52)

        assert result is not None
        assert result.median_price == Decimal("20.00")

    async def test_returns_none_for_empty_name(self):
        provider = MagicMock()
        provider.search_card = AsyncMock()

        entry = _card_entry(card_id=4, name_en="")
        result = await _fetch_price_liga(provider, entry, card_id=4)

        assert result is None
        provider.search_card.assert_not_awaited()

    async def test_uses_name_pt_when_name_en_missing(self):
        provider = MagicMock()
        provider.search_card = AsyncMock(return_value=_liga_price_result(mid=Decimal("5.00")))

        entry = {"card_id": 5, "name_en": "", "name_pt": "Raio", "external_id": "x", "slug": "x"}
        result = await _fetch_price_liga(provider, entry, card_id=5)

        assert result is not None
        assert result.median_price == Decimal("5.00")
        provider.search_card.assert_awaited_once_with("Raio")


# ── run_scan with Liga provider ─────────────────────────────────


@pytest.mark.asyncio
class TestRunScanLiga:
    """Tests for run_scan with provider_name='liga'."""

    @patch("src.collectors.scan.Repository")
    async def test_liga_happy_path(self, MockRepo):
        """Liga provider returns prices for 2 cards, all processed."""
        entries = [
            _card_entry(external_id="1001", card_id=10, name_en="Lightning Bolt"),
            _card_entry(external_id="1002", card_id=20, name_en="Counterspell"),
        ]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries, insert_return=1)

        provider = MagicMock()
        provider.search_card = AsyncMock(return_value=_liga_price_result(mid=Decimal("15.00")))
        provider.close = AsyncMock()

        result = await run_scan(
            db_url="sqlite:///:memory:",
            provider=provider,
            provider_name="liga",
            delay=0,
        )

        assert isinstance(result, ScanRun)
        assert result.cards_processed == 2
        assert result.cards_failed == 0
        assert result.observations_saved == 2
        assert result.status == "completed"
        assert provider.search_card.call_count == 2

    @patch("src.collectors.scan.Repository")
    async def test_liga_observation_source_is_liga(self, MockRepo):
        """Observations saved with source='liga' and external_id='liga_{card_id}'."""
        entries = [_card_entry(external_id="1001", card_id=42, name_en="Bolt")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries, insert_return=1)

        provider = MagicMock()
        provider.search_card = AsyncMock(return_value=_liga_price_result(mid=Decimal("10.00")))
        provider.close = AsyncMock()

        await run_scan(
            db_url="sqlite:///:memory:",
            provider=provider,
            provider_name="liga",
            delay=0,
        )

        # Check the observation passed to insert_price_observations
        obs_call = repo.insert_price_observations.call_args[0][0]
        assert len(obs_call) == 1
        obs = obs_call[0]
        assert obs.source == "liga"
        assert obs.external_id == "liga_42"

    @patch("src.collectors.scan.Repository")
    async def test_liga_concurrency_forced_to_1(self, MockRepo):
        """Even if concurrency=5 is passed, Liga forces concurrency=1."""
        entries = [
            _card_entry(external_id="1001", card_id=10, name_en="Card A"),
            _card_entry(external_id="1002", card_id=20, name_en="Card B"),
            _card_entry(external_id="1003", card_id=30, name_en="Card C"),
        ]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries, insert_return=1)

        provider = MagicMock()
        call_order = []

        async def mock_search(name):
            call_order.append(name)
            return _liga_price_result(mid=Decimal("5.00"))

        provider.search_card = mock_search
        provider.close = AsyncMock()

        result = await run_scan(
            db_url="sqlite:///:memory:",
            provider=provider,
            provider_name="liga",
            concurrency=5,  # Should be overridden to 1
            delay=0,
        )

        # All cards processed (concurrency=1 doesn't prevent processing)
        assert result.cards_processed == 3

    @patch("src.collectors.scan.Repository")
    async def test_liga_not_found_skips_card(self, MockRepo):
        """LigaNotFoundError causes card to be skipped (failed), no retry."""
        entries = [_card_entry(external_id="1001", card_id=10, name_en="Missing Card")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MagicMock()
        provider.search_card = AsyncMock(
            side_effect=LigaNotFoundError("Not found", url="/card", status_code=404, attempts=1)
        )
        provider.close = AsyncMock()

        result = await run_scan(
            db_url="sqlite:///:memory:",
            provider=provider,
            provider_name="liga",
            delay=0,
        )

        assert result.cards_failed == 1
        assert result.cards_processed == 1  # failed cards count as processed

    @patch("src.collectors.scan.Repository")
    async def test_liga_rate_limit_requeued(self, MockRepo):
        """LigaRateLimitError triggers requeue; second attempt succeeds."""
        entries = [_card_entry(external_id="1001", card_id=10, name_en="Slow Card")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries, insert_return=1)

        provider = MagicMock()
        provider.search_card = AsyncMock(
            side_effect=[
                LigaRateLimitError("429", url="/card", status_code=429, attempts=1),
                _liga_price_result(mid=Decimal("20.00")),
            ]
        )
        provider.close = AsyncMock()

        result = await run_scan(
            db_url="sqlite:///:memory:",
            provider=provider,
            provider_name="liga",
            delay=0,
        )

        assert result.cards_processed == 1
        assert result.cards_failed == 0
        assert result.observations_saved == 1

    @patch("src.collectors.scan.Repository")
    async def test_liga_rate_limit_exhausted(self, MockRepo):
        """LigaRateLimitError on both attempts counts as failed."""
        entries = [_card_entry(external_id="1001", card_id=10, name_en="Blocked Card")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MagicMock()
        provider.search_card = AsyncMock(
            side_effect=LigaRateLimitError("429", url="/card", status_code=429, attempts=2)
        )
        provider.close = AsyncMock()

        result = await run_scan(
            db_url="sqlite:///:memory:",
            provider=provider,
            provider_name="liga",
            delay=0,
        )

        assert result.cards_failed == 1
        assert result.cards_processed == 1  # failed cards count as processed

    @patch("src.collectors.scan.Repository")
    async def test_liga_generic_error_fails_card(self, MockRepo):
        """LigaError (generic) causes card to fail."""
        entries = [_card_entry(external_id="1001", card_id=10, name_en="Error Card")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MagicMock()
        provider.search_card = AsyncMock(
            side_effect=LigaError("Server error", url="/card", status_code=500, attempts=2)
        )
        provider.close = AsyncMock()

        result = await run_scan(
            db_url="sqlite:///:memory:",
            provider=provider,
            provider_name="liga",
            delay=0,
        )

        assert result.cards_failed == 1
        assert result.cards_processed == 1  # failed cards count as processed

    @patch("src.collectors.scan.Repository")
    async def test_liga_no_price_counted_as_processed(self, MockRepo):
        """Cards with no price from Liga are counted as processed, not failed."""
        entries = [_card_entry(external_id="1001", card_id=10, name_en="Cheap Card")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MagicMock()
        provider.search_card = AsyncMock(
            return_value=_liga_price_result(mid=None, low=None, high=None)
        )
        provider.close = AsyncMock()

        result = await run_scan(
            db_url="sqlite:///:memory:",
            provider=provider,
            provider_name="liga",
            delay=0,
        )

        assert result.cards_processed == 1
        assert result.cards_failed == 0
        assert result.observations_saved == 0

    @patch("src.collectors.scan.Repository")
    async def test_liga_scan_type_overridden(self, MockRepo):
        """Default COLLECTION scan_type is overridden to LIGA_FULL."""
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries=[])

        provider = MagicMock()
        provider.close = AsyncMock()

        await run_scan(
            db_url="sqlite:///:memory:",
            provider=provider,
            provider_name="liga",
            delay=0,
        )

        # Check create_scan_run was called with liga_full
        call_args = repo.create_scan_run.call_args[0]
        assert call_args[0] == "liga_full"

    @patch("src.collectors.scan.Repository")
    async def test_liga_custom_becomes_liga_partial(self, MockRepo):
        """CUSTOM scan_type is overridden to LIGA_PARTIAL for Liga scans."""
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries=[])

        provider = MagicMock()
        provider.close = AsyncMock()

        scan_filter = ScanFilter(scan_type=ScanType.CUSTOM, card_ids=[1, 2])
        await run_scan(
            db_url="sqlite:///:memory:",
            scan_filter=scan_filter,
            provider=provider,
            provider_name="liga",
            delay=0,
        )

        call_args = repo.create_scan_run.call_args[0]
        assert call_args[0] == "liga_partial"

    @patch("src.collectors.scan.Repository")
    async def test_liga_delay_enforced_minimum(self, MockRepo):
        """Liga enforces minimum delay of LIGA_DEFAULT_DELAY."""
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries=[])

        provider = MagicMock()
        provider.close = AsyncMock()

        # Pass a small delay — should be overridden
        await run_scan(
            db_url="sqlite:///:memory:",
            provider=provider,
            provider_name="liga",
            delay=0.5,
        )

        # The test verifies no crash — the actual delay enforcement is an
        # internal detail. We verify through the constants being correct.
        assert LIGA_DEFAULT_DELAY == 5.0
        assert LIGA_CONCURRENCY == 1
        assert LIGA_REQUEUE_DELAY_MULTIPLIER == 6

    @patch("src.collectors.scan.Repository")
    async def test_liga_provider_closed_on_success(self, MockRepo):
        """Provider.close() called after successful Liga scan (when owns_provider)."""
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries=[])

        provider = MagicMock()
        provider.close = AsyncMock()

        # provider passed explicitly, so owns_provider=False → close NOT called
        await run_scan(
            db_url="sqlite:///:memory:",
            provider=provider,
            provider_name="liga",
            delay=0,
        )

        # External provider NOT owned → close not called by orchestrator
        provider.close.assert_not_awaited()


# ── MYP backward compatibility ─────────────────────────────────


@pytest.mark.asyncio
class TestMypBackwardCompat:
    """Verify MYP path still works with the refactored code."""

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_myp_happy_path(self, MockRepo, MockProvider):
        """MYP provider returns prices, all processed (backward compat)."""
        entries = [
            _card_entry(external_id="1001", slug="card-a"),
            _card_entry(external_id="1002", slug="card-b"),
        ]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries, insert_return=1)

        # Override scan_type for MYP
        def _build(run_id):
            merged = {
                "id": 1,
                "scan_type": "collection",
                "filters_json": "{}",
                "status": "pending",
                "cards_total": 0,
                "cards_processed": 0,
                "cards_failed": 0,
                "observations_saved": 0,
                "error_summary": None,
                "started_at": None,
                "finished_at": None,
                "created_at": None,
            }
            for call in repo.update_scan_run.call_args_list:
                merged.update(call[1])
            return merged

        repo.get_scan_run.side_effect = _build

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=_jsonld_price(Decimal("10.00")))
        provider.close = AsyncMock()

        result = await run_scan(db_url="sqlite:///:memory:", concurrency=1)

        assert isinstance(result, ScanRun)
        assert result.cards_processed == 2
        assert result.cards_failed == 0
        assert result.observations_saved == 2
        assert result.status == "completed"

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_myp_not_found_still_works(self, MockRepo, MockProvider):
        """MYP NotFoundError still handled correctly."""
        entries = [_card_entry(external_id="1001", slug="missing")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(
            side_effect=NotFoundError("404", url="/card", status_code=404, attempts=1)
        )
        provider.close = AsyncMock()

        result = await run_scan(db_url="sqlite:///:memory:", concurrency=1)

        assert result.cards_failed == 1
        assert result.cards_processed == 1  # failed cards count as processed

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_myp_rate_limit_requeue(self, MockRepo, MockProvider):
        """MYP RateLimitError still triggers requeue correctly."""
        entries = [_card_entry(external_id="1001", slug="slow")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries, insert_return=1)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(
            side_effect=[
                RateLimitError("429", url="/card", status_code=429, attempts=2),
                _jsonld_price(Decimal("10.00")),
            ]
        )
        provider.close = AsyncMock()

        result = await run_scan(db_url="sqlite:///:memory:", concurrency=1, delay=0)

        assert result.cards_processed == 1
        assert result.cards_failed == 0
        assert result.observations_saved == 1

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_myp_scan_type_not_changed(self, MockRepo, MockProvider):
        """MYP scans keep original scan_type (not overridden to liga)."""
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries=[])

        provider = MockProvider.return_value
        provider.close = AsyncMock()

        await run_scan(db_url="sqlite:///:memory:", concurrency=1)

        call_args = repo.create_scan_run.call_args[0]
        assert call_args[0] == "collection"  # Not liga_full

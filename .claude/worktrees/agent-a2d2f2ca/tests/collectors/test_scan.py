"""Tests for the collection scan orchestrator (F13-T04).

Covers:
 1. Happy path: provider returns prices, ScanRun has correct counts
 2. Dry run: no price fetches, ScanRun populated with cards_total
 3. Filter by set: only cards matching set_code are processed
 4. Error handling: provider raises on one card, scan continues, cards_failed=1
 5. Failed status: when > 50% cards fail, status is "failed"
 6. Empty filter result: no cards match filter, scan completes with cards_total=0
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from src.collectors.scan import run_scan
from src.domain.models import JsonLdPrice, ScanFilter, ScanRun, ScanType
from src.providers.myp.exceptions import NotFoundError, RateLimitError

# ── helpers ──────────────────────────────────────────────────────


def _card_entry(
    external_id: str = "1000",
    slug: str = "lightning-bolt",
    card_id: int = 100,
    set_code: str = "LEA",
    name_en: str = "Lightning Bolt",
) -> dict:
    """Create a fake card entry dict as returned by get_cards_for_scan."""
    return {
        "external_id": external_id,
        "slug": slug,
        "card_id": card_id,
        "set_code": set_code,
        "name_en": name_en,
    }


def _jsonld_price(
    price: Decimal | None = Decimal("12.50"),
    currency: str = "BRL",
    availability: str = "InStock",
) -> JsonLdPrice:
    return JsonLdPrice(price=price, currency=currency, availability=availability)


def _make_scan_run_dict(
    run_id: int = 1,
    scan_type: str = "collection",
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
    repo_mock.insert_price_observations.return_value = insert_return

    # get_scan_run returns the final state -- we capture update_scan_run
    # calls and build the dict from the last call's kwargs.
    def _build_get_scan_run(run_id):
        # Merge all update_scan_run calls into one dict
        merged: dict = {
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
        for call in repo_mock.update_scan_run.call_args_list:
            merged.update(call[1])  # kwargs
        return merged

    repo_mock.get_scan_run.side_effect = _build_get_scan_run


# ── tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRunScan:
    """Tests for the async run_scan orchestrator."""

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_happy_path(self, MockRepo, MockProvider):
        """Provider returns prices for 3 cards, all processed and stored."""
        entries = [
            _card_entry(external_id="1001", slug="card-a"),
            _card_entry(external_id="1002", slug="card-b"),
            _card_entry(external_id="1003", slug="card-c"),
        ]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries, insert_return=1)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=_jsonld_price(Decimal("10.00")))
        provider.close = AsyncMock()

        result = await run_scan(db_url="sqlite:///:memory:", concurrency=1)

        assert isinstance(result, ScanRun)
        assert result.cards_total == 3
        assert result.cards_processed == 3
        assert result.cards_failed == 0
        assert result.observations_saved == 3
        assert result.status == "completed"
        assert provider.fetch_current_price.call_count == 3
        assert repo.insert_price_observations.call_count == 3

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_dry_run(self, MockRepo, MockProvider):
        """Dry run creates scan run and gets cards but does not fetch prices."""
        entries = [
            _card_entry(external_id="1001"),
            _card_entry(external_id="1002"),
        ]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock()
        provider.close = AsyncMock()

        result = await run_scan(db_url="sqlite:///:memory:", dry_run=True, concurrency=1)

        assert isinstance(result, ScanRun)
        assert result.cards_total == 2
        assert result.cards_processed == 0
        assert result.status == "completed"
        provider.fetch_current_price.assert_not_called()
        # scan_run was created in DB
        repo.create_scan_run.assert_called_once()

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_filter_by_set(self, MockRepo, MockProvider):
        """Only cards matching set filter are returned by repo and processed."""
        # The filter is passed to repo.get_cards_for_scan, which does the
        # filtering. We simulate that only matching cards are returned.
        entries = [
            _card_entry(external_id="2001", set_code="MH2", slug="card-mh2"),
        ]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries, insert_return=1)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=_jsonld_price(Decimal("5.00")))
        provider.close = AsyncMock()

        scan_filter = ScanFilter(set_codes=["MH2"])
        result = await run_scan(db_url="sqlite:///:memory:", scan_filter=scan_filter, concurrency=1)

        assert result.cards_total == 1
        assert result.cards_processed == 1
        assert result.observations_saved == 1
        # Verify the filter was passed to repository
        repo.get_cards_for_scan.assert_called_once_with(scan_filter)

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_error_handling_continues(self, MockRepo, MockProvider):
        """Provider raises on one card; scan continues, cards_failed=1."""
        entries = [
            _card_entry(external_id="1001", slug="fail-card"),
            _card_entry(external_id="1002", slug="ok-card"),
            _card_entry(external_id="1003", slug="ok-card-2"),
        ]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries, insert_return=1)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(
            side_effect=[
                RuntimeError("Network timeout"),
                _jsonld_price(Decimal("5.00")),
                _jsonld_price(Decimal("8.00")),
            ]
        )
        provider.close = AsyncMock()

        result = await run_scan(db_url="sqlite:///:memory:", concurrency=1)

        assert result.cards_total == 3
        assert result.cards_processed == 2
        assert result.cards_failed == 1
        assert result.observations_saved == 2
        assert result.status == "completed"  # 1/3 failed <= 50%

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_failed_status_over_50_percent_errors(self, MockRepo, MockProvider):
        """When > 50% cards fail, status is 'failed'."""
        entries = [
            _card_entry(external_id="1001", slug="fail-a"),
            _card_entry(external_id="1002", slug="fail-b"),
            _card_entry(external_id="1003", slug="ok-card"),
        ]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries, insert_return=1)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(
            side_effect=[
                RuntimeError("Timeout"),
                RuntimeError("Connection refused"),
                _jsonld_price(Decimal("5.00")),
            ]
        )
        provider.close = AsyncMock()

        result = await run_scan(db_url="sqlite:///:memory:", concurrency=1)

        assert result.cards_total == 3
        assert result.cards_failed == 2
        assert result.cards_processed == 1
        assert result.status == "failed"  # 2/3 > 50%

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_empty_filter_result(self, MockRepo, MockProvider):
        """No cards match filter, scan completes with cards_total=0."""
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries=[])

        provider = MockProvider.return_value
        provider.close = AsyncMock()

        result = await run_scan(db_url="sqlite:///:memory:", concurrency=1)

        assert result.cards_total == 0
        assert result.cards_processed == 0
        assert result.cards_failed == 0
        assert result.observations_saved == 0
        assert result.status == "completed"

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_provider_closed_on_success(self, MockRepo, MockProvider):
        """Provider.close() is called after successful scan."""
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries=[])

        provider = MockProvider.return_value
        provider.close = AsyncMock()

        await run_scan(db_url="sqlite:///:memory:")

        provider.close.assert_awaited_once()

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_provider_closed_on_error(self, MockRepo, MockProvider):
        """Provider.close() is called even when get_cards_for_scan raises."""
        repo = MockRepo.return_value
        repo.create_scan_run.return_value = 1
        repo.update_scan_run.return_value = None
        repo.get_cards_for_scan.side_effect = RuntimeError("db error")

        provider = MockProvider.return_value
        provider.close = AsyncMock()

        with pytest.raises(RuntimeError, match="db error"):
            await run_scan(db_url="sqlite:///:memory:")

        provider.close.assert_awaited_once()

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_scan_run_created_in_db(self, MockRepo, MockProvider):
        """Scan run row is created with correct scan_type and filter JSON."""
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries=[])

        provider = MockProvider.return_value
        provider.close = AsyncMock()

        scan_filter = ScanFilter(scan_type=ScanType.SET, set_codes=["MH2"])
        await run_scan(db_url="sqlite:///:memory:", scan_filter=scan_filter, concurrency=1)

        repo.create_scan_run.assert_called_once_with("set", scan_filter.to_json())

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_null_price_counted_as_processed(self, MockRepo, MockProvider):
        """Cards with null price are counted as processed, not failed."""
        entries = [_card_entry(external_id="1001")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=_jsonld_price(price=None))
        provider.close = AsyncMock()

        result = await run_scan(db_url="sqlite:///:memory:", concurrency=1)

        assert result.cards_processed == 1
        assert result.cards_failed == 0
        assert result.observations_saved == 0


# ── F45-T03: Scan requeue tests ──────────────────────────────────


@pytest.mark.asyncio
class TestScanRequeue:
    """Tests for typed exception handling and re-queue logic in scan."""

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_not_found_immediate_fail(self, MockRepo, MockProvider):
        """NotFoundError causes immediate fail, no requeue."""
        entries = [_card_entry(external_id="1001", slug="missing-card")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(
            side_effect=NotFoundError("HTTP 404", url="/card", status_code=404, attempts=1)
        )
        provider.close = AsyncMock()

        result = await run_scan(db_url="sqlite:///:memory:", concurrency=1)

        assert result.cards_failed == 1
        assert result.cards_processed == 0

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_rate_limit_requeue_then_success(self, MockRepo, MockProvider):
        """RateLimitError on first attempt triggers requeue; second attempt succeeds."""
        entries = [_card_entry(external_id="1001", slug="slow-card")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries, insert_return=1)

        # First call: RateLimitError; second call (retry): success
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
    async def test_rate_limit_requeue_exhausted(self, MockRepo, MockProvider):
        """RateLimitError on both attempts counts as failed."""
        entries = [_card_entry(external_id="1001", slug="slow-card")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(
            side_effect=RateLimitError("429", url="/card", status_code=429, attempts=2)
        )
        provider.close = AsyncMock()

        result = await run_scan(db_url="sqlite:///:memory:", concurrency=1, delay=0)

        assert result.cards_failed == 1
        assert result.cards_processed == 0

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_mixed_errors_correct_counts(self, MockRepo, MockProvider):
        """Mix of NotFoundError, RateLimitError (success on retry), and normal."""
        entries = [
            _card_entry(external_id="1001", slug="not-found"),
            _card_entry(external_id="1002", slug="rate-limited"),
            _card_entry(external_id="1003", slug="ok-card"),
        ]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries, insert_return=1)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(
            side_effect=[
                NotFoundError("404", url="/1001", status_code=404, attempts=1),
                RateLimitError("429", url="/1002", status_code=429, attempts=2),
                _jsonld_price(Decimal("5.00")),
                # Retry pass: rate-limited card succeeds
                _jsonld_price(Decimal("8.00")),
            ]
        )
        provider.close = AsyncMock()

        result = await run_scan(db_url="sqlite:///:memory:", concurrency=1, delay=0)

        assert result.cards_failed == 1  # only the 404
        assert result.cards_processed == 2  # ok-card + retried card
        assert result.observations_saved == 2

    @patch("src.collectors.scan.MypCardsProvider")
    @patch("src.collectors.scan.Repository")
    async def test_generic_exception_still_caught(self, MockRepo, MockProvider):
        """Generic exceptions are still caught by the fallback handler."""
        entries = [_card_entry(external_id="1001", slug="error-card")]
        repo = MockRepo.return_value
        _setup_repo_mock(repo, entries)

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(side_effect=RuntimeError("unexpected error"))
        provider.close = AsyncMock()

        result = await run_scan(db_url="sqlite:///:memory:", concurrency=1)

        assert result.cards_failed == 1
        assert result.cards_processed == 0

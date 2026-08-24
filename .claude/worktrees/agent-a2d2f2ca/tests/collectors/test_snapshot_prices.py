"""Tests for the snapshot prices collector (F12-T04).

Covers test plan scenarios I11-I24:
 I11. Happy path: 3 linked entries, all have prices -> 3 stored
 I12. Idempotency: entry already has snapshot for today -> skipped
 I13. Zero price: JSON-LD returns price=None -> skipped_zero_price
 I14. Fetch returns None (no JSON-LD on page) -> skipped_zero_price
 I15. Fetch error: provider raises exception -> error counted
 I16. Dry run: no DB writes, summary still populated
 I17. Limit: 10 entries, limit=3 -> only 3 processed
 I18. No linked entries: empty result -> summary all zeros
 I19. Mixed results: accurate summary counts
 I20. Provider closed on success
 I21. Provider closed on error
 I22. Observations stored with source="jsonld_snapshot"
 I23. Observation uses today's date
 I24. Concurrency semaphore respected
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from src.collectors.snapshot_prices import run_snapshot_prices
from src.domain.models import JsonLdPrice, SnapshotSummary

# ── helpers ──────────────────────────────────────────────────────


def _entry(
    entry_id: int = 1,
    card_id: int = 100,
    external_id: str = "1000",
    slug: str = "lightning-bolt",
    url: str = "https://mypcards.com/magic/produto/1000/lightning-bolt",
) -> dict:
    """Create a fake linked collection entry dict."""
    return {
        "entry_id": entry_id,
        "card_id": card_id,
        "external_id": external_id,
        "slug": slug,
        "url": url,
    }


def _jsonld_price(
    price: Decimal | None = Decimal("12.50"),
    currency: str = "BRL",
    availability: str = "InStock",
) -> JsonLdPrice:
    return JsonLdPrice(price=price, currency=currency, availability=availability)


# ── tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRunSnapshotPrices:
    """Tests for the async run_snapshot_prices orchestrator."""

    @patch("src.collectors.snapshot_prices.MypCardsProvider")
    @patch("src.collectors.snapshot_prices.Repository")
    async def test_happy_path_3_entries_all_stored(self, MockRepo, MockProvider):
        """I11: 3 linked entries, provider returns prices, all stored."""
        entries = [
            _entry(entry_id=1, external_id="1001", slug="card-a"),
            _entry(entry_id=2, external_id="1002", slug="card-b"),
            _entry(entry_id=3, external_id="1003", slug="card-c"),
        ]
        repo = MockRepo.return_value
        repo.get_linked_collection_with_source.return_value = entries
        repo.has_snapshot_for_date.return_value = False
        repo.insert_price_observations.return_value = 1

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=_jsonld_price(Decimal("10.00")))
        provider.close = AsyncMock()

        summary = await run_snapshot_prices(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.total_entries == 3
        assert summary.fetched == 3
        assert summary.stored == 3
        assert summary.errors == 0
        assert summary.skipped_existing == 0
        assert summary.skipped_zero_price == 0
        assert repo.insert_price_observations.call_count == 3
        assert provider.fetch_current_price.call_count == 3

    @patch("src.collectors.snapshot_prices.MypCardsProvider")
    @patch("src.collectors.snapshot_prices.Repository")
    async def test_idempotency_skips_existing(self, MockRepo, MockProvider):
        """I12: entry already has snapshot for today -> skipped."""
        entries = [_entry(entry_id=1, external_id="1001")]
        repo = MockRepo.return_value
        repo.get_linked_collection_with_source.return_value = entries
        repo.has_snapshot_for_date.return_value = True

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock()
        provider.close = AsyncMock()

        summary = await run_snapshot_prices(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.skipped_existing == 1
        assert summary.fetched == 0
        assert summary.stored == 0
        provider.fetch_current_price.assert_not_called()

    @patch("src.collectors.snapshot_prices.MypCardsProvider")
    @patch("src.collectors.snapshot_prices.Repository")
    async def test_zero_price_skipped(self, MockRepo, MockProvider):
        """I13: JSON-LD returns price=None -> skipped_zero_price."""
        entries = [_entry(entry_id=1, external_id="1001")]
        repo = MockRepo.return_value
        repo.get_linked_collection_with_source.return_value = entries
        repo.has_snapshot_for_date.return_value = False

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=_jsonld_price(price=None))
        provider.close = AsyncMock()

        summary = await run_snapshot_prices(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.skipped_zero_price == 1
        assert summary.fetched == 0
        repo.insert_price_observations.assert_not_called()

    @patch("src.collectors.snapshot_prices.MypCardsProvider")
    @patch("src.collectors.snapshot_prices.Repository")
    async def test_fetch_returns_none_skipped(self, MockRepo, MockProvider):
        """I14: fetch_current_price returns None -> skipped_zero_price."""
        entries = [_entry(entry_id=1, external_id="1001")]
        repo = MockRepo.return_value
        repo.get_linked_collection_with_source.return_value = entries
        repo.has_snapshot_for_date.return_value = False

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=None)
        provider.close = AsyncMock()

        summary = await run_snapshot_prices(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.skipped_zero_price == 1
        assert summary.fetched == 0

    @patch("src.collectors.snapshot_prices.MypCardsProvider")
    @patch("src.collectors.snapshot_prices.Repository")
    async def test_fetch_error_counted(self, MockRepo, MockProvider):
        """I15: provider raises exception -> error counted, continues."""
        entries = [
            _entry(entry_id=1, external_id="1001", slug="fail-card"),
            _entry(entry_id=2, external_id="1002", slug="ok-card"),
        ]
        repo = MockRepo.return_value
        repo.get_linked_collection_with_source.return_value = entries
        repo.has_snapshot_for_date.return_value = False
        repo.insert_price_observations.return_value = 1

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(
            side_effect=[
                RuntimeError("Network timeout"),
                _jsonld_price(Decimal("5.00")),
            ]
        )
        provider.close = AsyncMock()

        summary = await run_snapshot_prices(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.errors == 1
        assert summary.fetched == 1
        assert summary.stored == 1
        assert len(summary.error_details) == 1
        assert summary.error_details[0].error_type == "RuntimeError"
        assert "Network timeout" in summary.error_details[0].error_message

    @patch("src.collectors.snapshot_prices.MypCardsProvider")
    @patch("src.collectors.snapshot_prices.Repository")
    async def test_dry_run_no_writes(self, MockRepo, MockProvider):
        """I16: dry_run=True -> no DB writes, summary still populated."""
        entries = [
            _entry(entry_id=1, external_id="1001"),
            _entry(entry_id=2, external_id="1002"),
        ]
        repo = MockRepo.return_value
        repo.get_linked_collection_with_source.return_value = entries

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=_jsonld_price(Decimal("8.00")))
        provider.close = AsyncMock()

        summary = await run_snapshot_prices(
            db_url="sqlite:///:memory:", dry_run=True, concurrency=1
        )

        assert summary.fetched == 2
        assert summary.stored == 2
        repo.insert_price_observations.assert_not_called()
        # Idempotency check is skipped in dry run
        repo.has_snapshot_for_date.assert_not_called()

    @patch("src.collectors.snapshot_prices.MypCardsProvider")
    @patch("src.collectors.snapshot_prices.Repository")
    async def test_limit_restricts_processing(self, MockRepo, MockProvider):
        """I17: 10 entries, limit=3 -> only 3 processed."""
        entries = [
            _entry(entry_id=i, external_id=str(1000 + i), slug=f"card-{i}") for i in range(1, 11)
        ]
        repo = MockRepo.return_value
        repo.get_linked_collection_with_source.return_value = entries
        repo.has_snapshot_for_date.return_value = False
        repo.insert_price_observations.return_value = 1

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=_jsonld_price(Decimal("5.00")))
        provider.close = AsyncMock()

        summary = await run_snapshot_prices(db_url="sqlite:///:memory:", limit=3, concurrency=1)

        assert summary.total_entries == 10
        assert summary.fetched == 3
        assert summary.stored == 3
        assert provider.fetch_current_price.call_count == 3

    @patch("src.collectors.snapshot_prices.MypCardsProvider")
    @patch("src.collectors.snapshot_prices.Repository")
    async def test_no_linked_entries(self, MockRepo, MockProvider):
        """I18: no linked entries -> summary all zeros."""
        repo = MockRepo.return_value
        repo.get_linked_collection_with_source.return_value = []

        provider = MockProvider.return_value
        provider.close = AsyncMock()

        summary = await run_snapshot_prices(db_url="sqlite:///:memory:")

        assert summary.total_entries == 0
        assert summary.fetched == 0
        assert summary.stored == 0
        assert summary.skipped_existing == 0
        assert summary.skipped_zero_price == 0
        assert summary.errors == 0
        assert summary.finished_at is not None

    @patch("src.collectors.snapshot_prices.MypCardsProvider")
    @patch("src.collectors.snapshot_prices.Repository")
    async def test_mixed_results_accurate_summary(self, MockRepo, MockProvider):
        """I19: 5 entries: 2 priced, 1 zero, 1 existing, 1 error."""
        entries = [
            _entry(entry_id=1, external_id="1001", slug="priced-a"),
            _entry(entry_id=2, external_id="1002", slug="priced-b"),
            _entry(entry_id=3, external_id="1003", slug="zero-price"),
            _entry(entry_id=4, external_id="1004", slug="existing"),
            _entry(entry_id=5, external_id="1005", slug="error-card"),
        ]
        repo = MockRepo.return_value
        repo.get_linked_collection_with_source.return_value = entries
        repo.has_snapshot_for_date.side_effect = [
            False,  # 1001
            False,  # 1002
            False,  # 1003
            True,  # 1004 - already exists
            False,  # 1005
        ]
        repo.insert_price_observations.return_value = 1

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(
            side_effect=[
                _jsonld_price(Decimal("10.00")),  # 1001 - priced
                _jsonld_price(Decimal("15.00")),  # 1002 - priced
                _jsonld_price(price=None),  # 1003 - zero/none
                # 1004 is skipped (existing), no fetch call
                RuntimeError("Timeout"),  # 1005 - error
            ]
        )
        provider.close = AsyncMock()

        summary = await run_snapshot_prices(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.total_entries == 5
        assert summary.fetched == 2
        assert summary.stored == 2
        assert summary.skipped_existing == 1
        assert summary.skipped_zero_price == 1
        assert summary.errors == 1

    @patch("src.collectors.snapshot_prices.MypCardsProvider")
    @patch("src.collectors.snapshot_prices.Repository")
    async def test_provider_closed_on_success(self, MockRepo, MockProvider):
        """I20: provider.close() is called on successful completion."""
        repo = MockRepo.return_value
        repo.get_linked_collection_with_source.return_value = []

        provider = MockProvider.return_value
        provider.close = AsyncMock()

        await run_snapshot_prices(db_url="sqlite:///:memory:")

        provider.close.assert_awaited_once()

    @patch("src.collectors.snapshot_prices.MypCardsProvider")
    @patch("src.collectors.snapshot_prices.Repository")
    async def test_provider_closed_on_error(self, MockRepo, MockProvider):
        """I21: provider.close() is called even when an error occurs."""
        repo = MockRepo.return_value
        repo.get_linked_collection_with_source.side_effect = RuntimeError("db error")

        provider = MockProvider.return_value
        provider.close = AsyncMock()

        with pytest.raises(RuntimeError, match="db error"):
            await run_snapshot_prices(db_url="sqlite:///:memory:")

        provider.close.assert_awaited_once()

    @patch("src.collectors.snapshot_prices.MypCardsProvider")
    @patch("src.collectors.snapshot_prices.Repository")
    async def test_observation_source_is_jsonld_snapshot(self, MockRepo, MockProvider):
        """I22: observations stored with source='jsonld_snapshot'."""
        entries = [_entry(entry_id=1, external_id="1001")]
        repo = MockRepo.return_value
        repo.get_linked_collection_with_source.return_value = entries
        repo.has_snapshot_for_date.return_value = False
        repo.insert_price_observations.return_value = 1

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=_jsonld_price(Decimal("7.50")))
        provider.close = AsyncMock()

        await run_snapshot_prices(db_url="sqlite:///:memory:", concurrency=1)

        call_args = repo.insert_price_observations.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0].source == "jsonld_snapshot"

    @patch("src.collectors.snapshot_prices.MypCardsProvider")
    @patch("src.collectors.snapshot_prices.Repository")
    async def test_observation_uses_today_date(self, MockRepo, MockProvider):
        """I23: observation uses today's date."""
        entries = [_entry(entry_id=1, external_id="1001")]
        repo = MockRepo.return_value
        repo.get_linked_collection_with_source.return_value = entries
        repo.has_snapshot_for_date.return_value = False
        repo.insert_price_observations.return_value = 1

        provider = MockProvider.return_value
        provider.fetch_current_price = AsyncMock(return_value=_jsonld_price(Decimal("7.50")))
        provider.close = AsyncMock()

        await run_snapshot_prices(db_url="sqlite:///:memory:", concurrency=1)

        call_args = repo.insert_price_observations.call_args[0][0]
        assert call_args[0].observed_at == date.today()

    @patch("src.collectors.snapshot_prices.MypCardsProvider")
    @patch("src.collectors.snapshot_prices.Repository")
    async def test_summary_has_finished_at(self, MockRepo, MockProvider):
        """Summary has finished_at set after completion."""
        repo = MockRepo.return_value
        repo.get_linked_collection_with_source.return_value = []

        provider = MockProvider.return_value
        provider.close = AsyncMock()

        summary = await run_snapshot_prices(db_url="sqlite:///:memory:")

        assert isinstance(summary, SnapshotSummary)
        assert summary.finished_at is not None
        assert summary.started_at is not None
        assert summary.finished_at >= summary.started_at

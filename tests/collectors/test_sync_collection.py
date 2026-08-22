"""Tests for the collection sync orchestrator (F10-T06).

Covers test plan scenarios 27-33:
 27. Matched card flow: creates CardRow, SourceCardRow, PriceObservations, links user_collection
 28. Unmatched cards: logged, card_id remains NULL
 29. skip_matched=True skips entries where card_id IS NOT NULL
 30. dry_run=True does not call any repository write methods
 31. Provider exception does not abort the entire sync (graceful degradation)
 32. SyncSummary counts are accurate
 33. Collection entries without name_en are skipped and counted
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.collection.converter import row_to_collection_entry
from src.collection.matcher import CollectionEntry
from src.collectors.sync_collection import (
    run_sync_collection,
)
from src.domain.models import (
    CardIdentity,
    HistoricalPrice,
    MypSearchResult,
    SourceCard,
    SyncSummary,
)
from src.providers.myp.exceptions import NotFoundError, RateLimitError

# ── fixtures ────────────────────────────────────────────────────


def _fake_row(
    id: int = 1,
    set_code: str = "dmr",
    collector_number: str = "123",
    name_en: str | None = "Lightning Bolt",
    name_pt: str | None = None,
    user_id: str = "eduardo",
    card_id: int | None = None,
) -> MagicMock:
    """Create a mock UserCollectionRow."""
    row = MagicMock()
    row.id = id
    row.set_code = set_code
    row.collector_number = collector_number
    row.name_en = name_en
    row.name_pt = name_pt
    row.user_id = user_id
    row.card_id = card_id
    return row


def _search_result(
    external_id: str = "1000",
    name: str = "Lightning Bolt",
    slug: str = "lightning-bolt",
    sku: str | None = "magic_dmr_123",
    set_code: str | None = "dmr",
    collector_number: str | None = "123",
) -> MypSearchResult:
    return MypSearchResult(
        external_id=external_id,
        name=name,
        slug=slug,
        url=f"https://mypcards.com/magic/produto/{external_id}/{slug}",
        sku=sku,
        set_code=set_code,
        collector_number=collector_number,
    )


def _detailed_source_card(
    external_id: str = "1000",
    slug: str = "lightning-bolt",
    sku: str = "magic_dmr_123",
    name_en: str = "Lightning Bolt",
    name_pt: str = "Relampago",
    set_code: str = "dmr",
    collector_number: str = "123",
) -> SourceCard:
    return SourceCard(
        source="myp",
        external_id=external_id,
        url=f"https://mypcards.com/magic/produto/{external_id}/{slug}",
        sku=sku,
        identity=CardIdentity(
            game="magic",
            name_en=name_en,
            name_pt=name_pt,
            set_code=set_code,
            collector_number=collector_number,
        ),
    )


def _history_prices(external_id: str = "1000", count: int = 3) -> list[HistoricalPrice]:
    from datetime import date, timedelta
    from decimal import Decimal

    base_date = date(2026, 1, 1)
    return [
        HistoricalPrice(
            source="myp",
            external_id=external_id,
            observed_at=base_date + timedelta(days=i),
            median_price=Decimal("10.00") + Decimal(str(i)),
        )
        for i in range(count)
    ]


# ── unit tests: row_to_collection_entry ───────────────────────


class TestRowToEntry:
    """row_to_collection_entry converts a DB row to CollectionEntry."""

    def test_converts_all_fields(self):
        row = _fake_row(set_code="ltr", collector_number="42", name_en="Gandalf")
        entry = row_to_collection_entry(row)

        assert isinstance(entry, CollectionEntry)
        assert entry.set_code == "ltr"
        assert entry.collector_number == "42"
        assert entry.name_en == "Gandalf"

    def test_none_name_en(self):
        row = _fake_row(name_en=None)
        entry = row_to_collection_entry(row)

        assert entry.name_en is None


# ── unit tests: SyncSummary dataclass ─────────────────────────


class TestSyncSummary:
    """SyncSummary initializes with correct defaults."""

    def test_default_values(self):
        s = SyncSummary()
        assert s.total_entries == 0
        assert s.skipped_already_linked == 0
        assert s.searched == 0
        assert s.matched == 0
        assert s.ambiguous == 0
        assert s.unmatched == 0
        assert s.cards_created == 0
        assert s.observations_saved == 0
        assert s.errors == []
        assert s.results == []
        assert s.started_at is not None
        assert s.finished_at is None


# ── integration tests: run_sync_collection ────────────────────


@pytest.mark.asyncio
class TestRunSyncCollection:
    """Tests for the async run_sync_collection orchestrator."""

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_matched_card_full_pipeline(self, MockRepo, MockProvider):
        """Scenario 27: matched card creates CardRow, SourceCardRow,
        inserts PriceObservations, and links user_collection entry."""
        rows = [_fake_row(id=1, set_code="dmr", collector_number="123", name_en="Lightning Bolt")]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows
        repo.upsert_card.return_value = 42
        repo.upsert_source_card.return_value = 100
        repo.insert_price_observations.return_value = 3

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(return_value=[_search_result()])
        provider.get_card_details = AsyncMock(return_value=_detailed_source_card())
        provider.get_price_history = AsyncMock(return_value=_history_prices())
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.total_entries == 1
        assert summary.matched == 1
        assert summary.cards_created == 1
        assert summary.observations_saved == 3
        assert summary.searched == 1
        assert len(summary.errors) == 0

        # Verify repo writes
        repo.upsert_card.assert_called_once()
        repo.upsert_source_card.assert_called_once()
        repo.insert_price_observations.assert_called_once()
        repo.link_collection_entry.assert_called_once_with(1, 42)
        repo.mark_errors_resolved.assert_called_once_with("myp", "1000")

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_unmatched_card_not_stored(self, MockRepo, MockProvider):
        """Scenario 28: unmatched cards are logged but not stored."""
        rows = [_fake_row(id=1, name_en="Obscure Card", set_code="xyz", collector_number="999")]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(return_value=[])
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.total_entries == 1
        assert summary.unmatched == 1
        assert summary.matched == 0
        assert summary.searched == 1

        # No DB writes for unmatched cards
        repo.upsert_card.assert_not_called()
        repo.upsert_source_card.assert_not_called()
        repo.insert_price_observations.assert_not_called()
        repo.link_collection_entry.assert_not_called()

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_skip_matched_true_skips_linked(self, MockRepo, MockProvider):
        """Scenario 29: skip_matched=True skips entries where card_id IS NOT NULL."""
        rows = [
            _fake_row(id=1, name_en="Already Linked", card_id=10),
            _fake_row(
                id=2,
                name_en="Not Linked",
                card_id=None,
                set_code="ltr",
                collector_number="42",
            ),
        ]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows
        repo.upsert_card.return_value = 50
        repo.upsert_source_card.return_value = 200
        repo.insert_price_observations.return_value = 3

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(
            return_value=[
                _search_result(
                    external_id="2000",
                    set_code="ltr",
                    collector_number="42",
                    name="Not Linked",
                    slug="not-linked",
                    sku="magic_ltr_42",
                )
            ]
        )
        provider.get_card_details = AsyncMock(
            return_value=_detailed_source_card(
                external_id="2000",
                slug="not-linked",
                sku="magic_ltr_42",
                name_en="Not Linked",
                set_code="ltr",
                collector_number="42",
            )
        )
        provider.get_price_history = AsyncMock(return_value=_history_prices("2000"))
        provider.close = AsyncMock()

        summary = await run_sync_collection(
            db_url="sqlite:///:memory:", skip_matched=True, concurrency=1
        )

        assert summary.total_entries == 2
        assert summary.skipped_already_linked == 1
        assert summary.matched == 1
        # Only one card was searched
        assert summary.searched == 1
        assert provider.search_card.call_count == 1

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_skip_matched_false_processes_all(self, MockRepo, MockProvider):
        """skip_matched=False processes all entries, including already linked ones."""
        rows = [
            _fake_row(
                id=1,
                name_en="Already Linked",
                card_id=10,
                set_code="dmr",
                collector_number="123",
            ),
        ]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows
        repo.upsert_card.return_value = 10
        repo.upsert_source_card.return_value = 100
        repo.insert_price_observations.return_value = 3

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(return_value=[_search_result()])
        provider.get_card_details = AsyncMock(return_value=_detailed_source_card())
        provider.get_price_history = AsyncMock(return_value=_history_prices())
        provider.close = AsyncMock()

        summary = await run_sync_collection(
            db_url="sqlite:///:memory:", skip_matched=False, concurrency=1
        )

        assert summary.total_entries == 1
        assert summary.skipped_already_linked == 0
        assert summary.searched == 1
        assert summary.matched == 1

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_dry_run_no_writes(self, MockRepo, MockProvider):
        """Scenario 30: dry_run=True does not call any repository write methods."""
        rows = [_fake_row(id=1, set_code="dmr", collector_number="123", name_en="Lightning Bolt")]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(return_value=[_search_result()])
        provider.get_card_details = AsyncMock(return_value=_detailed_source_card())
        provider.get_price_history = AsyncMock(return_value=_history_prices())
        provider.close = AsyncMock()

        summary = await run_sync_collection(
            db_url="sqlite:///:memory:", dry_run=True, concurrency=1
        )

        assert summary.matched == 1
        # Dry run still counts observations
        assert summary.observations_saved == 3

        # No DB writes in dry-run mode
        repo.upsert_card.assert_not_called()
        repo.upsert_source_card.assert_not_called()
        repo.insert_price_observations.assert_not_called()
        repo.link_collection_entry.assert_not_called()
        repo.mark_errors_resolved.assert_not_called()

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_error_does_not_abort_sync(self, MockRepo, MockProvider):
        """Scenario 31: provider exception on one card does not abort the entire sync."""
        rows = [
            _fake_row(id=1, name_en="Failing Card", set_code="dmr", collector_number="1"),
            _fake_row(id=2, name_en="Successful Card", set_code="ltr", collector_number="42"),
        ]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows
        repo.upsert_card.return_value = 50
        repo.upsert_source_card.return_value = 200
        repo.insert_price_observations.return_value = 3

        provider = MockProvider.return_value
        # First card: search succeeds, but get_card_details raises
        provider.search_card = AsyncMock(
            side_effect=[
                [
                    _search_result(
                        external_id="1001",
                        set_code="dmr",
                        collector_number="1",
                        name="Failing Card",
                        slug="failing-card",
                        sku="magic_dmr_1",
                    )
                ],
                [
                    _search_result(
                        external_id="2000",
                        set_code="ltr",
                        collector_number="42",
                        name="Successful Card",
                        slug="successful-card",
                        sku="magic_ltr_42",
                    )
                ],
            ]
        )
        provider.get_card_details = AsyncMock(
            side_effect=[
                RuntimeError("Network timeout"),
                _detailed_source_card(
                    external_id="2000",
                    slug="successful-card",
                    sku="magic_ltr_42",
                    name_en="Successful Card",
                    set_code="ltr",
                    collector_number="42",
                ),
            ]
        )
        provider.get_price_history = AsyncMock(return_value=_history_prices("2000"))
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        # The sync did NOT abort
        assert summary.searched == 2
        assert summary.matched == 1
        assert len(summary.errors) == 1
        assert summary.errors[0].error_type == "RuntimeError"
        assert "Network timeout" in summary.errors[0].error_message

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_summary_counts_accuracy(self, MockRepo, MockProvider):
        """Scenario 32: SyncSummary counts are accurate for mixed results."""
        rows = [
            _fake_row(id=1, set_code="dmr", collector_number="123", name_en="Lightning Bolt"),
            _fake_row(id=2, set_code="ltr", collector_number="42", name_en="Gandalf"),
            _fake_row(id=3, set_code="xyz", collector_number="999", name_en="No Match Card"),
            _fake_row(id=4, set_code="neo", collector_number="1", name_en="Ambiguous Name"),
            _fake_row(id=5, set_code="m21", collector_number="50", name_en=None),
            _fake_row(
                id=6,
                set_code="dmr",
                collector_number="456",
                name_en="Already Linked",
                card_id=99,
            ),
        ]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows
        repo.upsert_card.return_value = 42
        repo.upsert_source_card.return_value = 100
        repo.insert_price_observations.return_value = 5

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(
            side_effect=[
                # Card 1: SKU exact match
                [_search_result()],
                # Card 2: SKU match
                [
                    _search_result(
                        external_id="2000",
                        set_code="ltr",
                        collector_number="42",
                        name="Gandalf",
                        slug="gandalf",
                        sku="magic_ltr_42",
                    )
                ],
                # Card 3: no results → unmatched
                [],
                # Card 4: ambiguous (multiple name matches, no SKU)
                [
                    _search_result(
                        external_id="4000",
                        name="Ambiguous Name",
                        slug="amb1",
                        sku=None,
                        set_code=None,
                        collector_number=None,
                    ),
                    _search_result(
                        external_id="4001",
                        name="Ambiguous Name",
                        slug="amb2",
                        sku=None,
                        set_code=None,
                        collector_number=None,
                    ),
                ],
                # Card 5 has no name_en → skipped before search
            ]
        )
        provider.get_card_details = AsyncMock(
            side_effect=[
                _detailed_source_card(),
                _detailed_source_card(
                    external_id="2000",
                    slug="gandalf",
                    sku="magic_ltr_42",
                    name_en="Gandalf",
                    set_code="ltr",
                    collector_number="42",
                ),
            ]
        )
        provider.get_price_history = AsyncMock(return_value=_history_prices(count=5))
        provider.close = AsyncMock()

        summary = await run_sync_collection(
            db_url="sqlite:///:memory:", skip_matched=True, concurrency=1
        )

        assert summary.total_entries == 6
        assert summary.skipped_already_linked == 1
        assert summary.searched == 4  # 5 minus the no-name, which is not searched
        assert summary.matched == 2
        assert summary.unmatched == 1
        assert summary.ambiguous == 1
        assert summary.cards_created == 2
        assert summary.observations_saved == 10  # 5 * 2 matched cards
        assert len(summary.errors) == 0

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_no_name_entry_skipped(self, MockRepo, MockProvider):
        """Scenario 33: entries without name_en are skipped and counted."""
        rows = [
            _fake_row(id=1, name_en=None, set_code="prm", collector_number="1"),
            _fake_row(id=2, name_en="Lightning Bolt", set_code="dmr", collector_number="123"),
        ]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows
        repo.upsert_card.return_value = 42
        repo.upsert_source_card.return_value = 100
        repo.insert_price_observations.return_value = 3

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(return_value=[_search_result()])
        provider.get_card_details = AsyncMock(return_value=_detailed_source_card())
        provider.get_price_history = AsyncMock(return_value=_history_prices())
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        # Only the card with name_en was searched
        assert summary.searched == 1
        assert provider.search_card.call_count == 1
        # The no-name entry is in results with status "no_name"
        no_name_results = [r for r in summary.results if r.status == "no_name"]
        assert len(no_name_results) == 1
        assert no_name_results[0].entry_id == 1

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_limit_restricts_processing(self, MockRepo, MockProvider):
        """--limit flag restricts the number of entries processed."""
        rows = [
            _fake_row(id=i, name_en=f"Card {i}", set_code="dmr", collector_number=str(i))
            for i in range(1, 11)
        ]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(return_value=[])
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", limit=3, concurrency=1)

        assert summary.total_entries == 10
        # Only 3 entries processed
        assert summary.searched == 3
        assert provider.search_card.call_count == 3

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_ambiguous_card_not_stored(self, MockRepo, MockProvider):
        """Ambiguous matches are logged but not stored."""
        rows = [_fake_row(id=1, set_code="m21", collector_number="152", name_en="Lightning Bolt")]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(
            return_value=[
                _search_result(
                    external_id="7000",
                    name="Lightning Bolt",
                    sku=None,
                    set_code=None,
                    collector_number=None,
                ),
                _search_result(
                    external_id="7001",
                    name="Lightning Bolt",
                    slug="bolt-2",
                    sku=None,
                    set_code=None,
                    collector_number=None,
                ),
            ]
        )
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.ambiguous == 1
        assert summary.matched == 0

        # No DB writes for ambiguous cards
        repo.upsert_card.assert_not_called()
        repo.upsert_source_card.assert_not_called()
        repo.insert_price_observations.assert_not_called()
        repo.link_collection_entry.assert_not_called()

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_provider_closed_on_success(self, MockRepo, MockProvider):
        """Provider.close() is called on successful completion."""
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = []

        provider = MockProvider.return_value
        provider.close = AsyncMock()

        await run_sync_collection(db_url="sqlite:///:memory:")

        provider.close.assert_awaited_once()

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_provider_closed_on_error(self, MockRepo, MockProvider):
        """Provider.close() is called even when an error occurs."""
        repo = MockRepo.return_value
        repo.get_all_collection_entries.side_effect = RuntimeError("db error")

        provider = MockProvider.return_value
        provider.close = AsyncMock()

        with pytest.raises(RuntimeError, match="db error"):
            await run_sync_collection(db_url="sqlite:///:memory:")

        provider.close.assert_awaited_once()

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_empty_collection(self, MockRepo, MockProvider):
        """Empty collection produces a valid (zero) summary."""
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = []

        provider = MockProvider.return_value
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:")

        assert summary.total_entries == 0
        assert summary.matched == 0
        assert summary.unmatched == 0
        assert summary.searched == 0
        assert summary.finished_at is not None

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_empty_history_still_links(self, MockRepo, MockProvider):
        """Card with empty history is still linked -- just no price data."""
        rows = [_fake_row(id=1, set_code="dmr", collector_number="123", name_en="Lightning Bolt")]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows
        repo.upsert_card.return_value = 42
        repo.upsert_source_card.return_value = 100
        repo.insert_price_observations.return_value = 0

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(return_value=[_search_result()])
        provider.get_card_details = AsyncMock(return_value=_detailed_source_card())
        provider.get_price_history = AsyncMock(return_value=[])  # Empty history
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.matched == 1
        assert summary.observations_saved == 0
        # Card is still linked even with no history
        repo.link_collection_entry.assert_called_once_with(1, 42)

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_card_page_parse_failure(self, MockRepo, MockProvider):
        """get_card_details returning None raises ValueError, counted as error."""
        rows = [_fake_row(id=1, set_code="dmr", collector_number="123", name_en="Lightning Bolt")]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(return_value=[_search_result()])
        provider.get_card_details = AsyncMock(return_value=None)  # Parse failure
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        assert len(summary.errors) == 1
        assert summary.errors[0].error_type == "ValueError"
        assert summary.matched == 0

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_sync_result_contains_match_confidence(self, MockRepo, MockProvider):
        """SyncResult records match confidence for synced cards."""
        rows = [_fake_row(id=1, set_code="dmr", collector_number="123", name_en="Lightning Bolt")]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows
        repo.upsert_card.return_value = 42
        repo.upsert_source_card.return_value = 100
        repo.insert_price_observations.return_value = 3

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(return_value=[_search_result()])
        provider.get_card_details = AsyncMock(return_value=_detailed_source_card())
        provider.get_price_history = AsyncMock(return_value=_history_prices())
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        assert len(summary.results) == 1
        result = summary.results[0]
        assert result.status == "synced"
        assert result.match_confidence == "sku_exact"
        assert result.card_id == 42
        assert result.observations_count == 3

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_pt_fallback_used_when_en_returns_empty(self, MockRepo, MockProvider):
        """When EN search returns nothing and name_pt exists, retry with PT name."""
        rows = [
            _fake_row(
                id=1,
                set_code="dmr",
                collector_number="123",
                name_en="Lightning Bolt",
                name_pt="Relampago",
            )
        ]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows
        repo.upsert_card.return_value = 42
        repo.upsert_source_card.return_value = 100
        repo.insert_price_observations.return_value = 3

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(
            side_effect=[
                [],  # EN search returns nothing
                [_search_result()],  # PT search returns a result
            ]
        )
        provider.get_card_details = AsyncMock(return_value=_detailed_source_card())
        provider.get_price_history = AsyncMock(return_value=_history_prices())
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.matched == 1
        assert summary.searched == 1
        # Two search calls: EN then PT
        assert provider.search_card.call_count == 2
        provider.search_card.assert_any_call("Lightning Bolt")
        provider.search_card.assert_any_call("Relampago")

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_pt_fallback_not_used_when_en_succeeds(self, MockRepo, MockProvider):
        """When EN search returns results, PT fallback is not triggered."""
        rows = [
            _fake_row(
                id=1,
                set_code="dmr",
                collector_number="123",
                name_en="Lightning Bolt",
                name_pt="Relampago",
            )
        ]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows
        repo.upsert_card.return_value = 42
        repo.upsert_source_card.return_value = 100
        repo.insert_price_observations.return_value = 3

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(return_value=[_search_result()])
        provider.get_card_details = AsyncMock(return_value=_detailed_source_card())
        provider.get_price_history = AsyncMock(return_value=_history_prices())
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.matched == 1
        # Only one search call (EN only)
        assert provider.search_card.call_count == 1
        provider.search_card.assert_called_once_with("Lightning Bolt")

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_pt_fallback_not_used_when_name_pt_is_none(self, MockRepo, MockProvider):
        """When name_pt is None, no fallback search is attempted."""
        rows = [
            _fake_row(
                id=1,
                set_code="xyz",
                collector_number="999",
                name_en="Obscure Card",
                name_pt=None,
            )
        ]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(return_value=[])
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.unmatched == 1
        # Only one search call (EN only, no PT fallback)
        assert provider.search_card.call_count == 1

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_pt_fallback_still_unmatched(self, MockRepo, MockProvider):
        """PT fallback search returns results but none match the entry."""
        rows = [
            _fake_row(
                id=1,
                set_code="xyz",
                collector_number="999",
                name_en="Obscure Card",
                name_pt="Carta Obscura",
            )
        ]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(
            side_effect=[
                [],  # EN returns nothing
                [
                    _search_result(
                        external_id="9000",
                        name="Carta Diferente",
                        slug="carta-diferente",
                        sku=None,
                        set_code=None,
                        collector_number=None,
                    )
                ],  # PT returns unrelated card
            ]
        )
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.unmatched == 1
        assert summary.matched == 0
        assert provider.search_card.call_count == 2

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_pt_fallback_also_empty(self, MockRepo, MockProvider):
        """Both EN and PT searches return empty lists."""
        rows = [
            _fake_row(
                id=1,
                set_code="xyz",
                collector_number="999",
                name_en="Obscure Card",
                name_pt="Carta Obscura",
            )
        ]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(return_value=[])
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.unmatched == 1
        assert provider.search_card.call_count == 2

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_upsert_card_returns_none_no_link(self, MockRepo, MockProvider):
        """If upsert_card returns None (no identity), card_id is not linked."""
        rows = [_fake_row(id=1, set_code="dmr", collector_number="123", name_en="Lightning Bolt")]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows
        repo.upsert_card.return_value = None  # No identity -> None
        repo.upsert_source_card.return_value = 100
        repo.insert_price_observations.return_value = 3

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(return_value=[_search_result()])
        provider.get_card_details = AsyncMock(return_value=_detailed_source_card())
        provider.get_price_history = AsyncMock(return_value=_history_prices())
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.matched == 1
        assert summary.cards_created == 0  # card_id is None
        repo.link_collection_entry.assert_not_called()


# ── F45-T04: Sync typed exception + requeue tests ────────────────


@pytest.mark.asyncio
class TestSyncTypedExceptions:
    """Tests for typed exception handling and re-queue in sync orchestrator."""

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_not_found_permanent_fail(self, MockRepo, MockProvider):
        """NotFoundError is recorded as not_found status, no requeue."""
        rows = [_fake_row(id=1, set_code="dmr", collector_number="123", name_en="Lightning Bolt")]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(
            side_effect=NotFoundError("HTTP 404", url="/search", status_code=404, attempts=1)
        )
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.not_found == 1
        assert len(summary.errors) == 1
        assert summary.errors[0].error_type == "NotFoundError"
        not_found_results = [r for r in summary.results if r.status == "not_found"]
        assert len(not_found_results) == 1

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_rate_limit_requeue_then_success(self, MockRepo, MockProvider):
        """RateLimitError on first attempt triggers requeue; second succeeds."""
        rows = [_fake_row(id=1, set_code="dmr", collector_number="123", name_en="Lightning Bolt")]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows
        repo.upsert_card.return_value = 42
        repo.upsert_source_card.return_value = 100
        repo.insert_price_observations.return_value = 3

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(
            side_effect=[
                RateLimitError("429", url="/search", status_code=429, attempts=2),
                [_search_result()],  # retry succeeds
            ]
        )
        provider.get_card_details = AsyncMock(return_value=_detailed_source_card())
        provider.get_price_history = AsyncMock(return_value=_history_prices())
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1, delay=0)

        assert summary.matched == 1
        assert summary.rate_limited == 0  # succeeded on retry

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_rate_limit_exhausted(self, MockRepo, MockProvider):
        """RateLimitError on all attempts is recorded as rate_limited."""
        rows = [_fake_row(id=1, set_code="dmr", collector_number="123", name_en="Lightning Bolt")]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(
            side_effect=RateLimitError("429", url="/search", status_code=429, attempts=2)
        )
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1, delay=0)

        assert summary.rate_limited == 1
        assert len(summary.errors) == 1
        assert summary.errors[0].error_type == "RateLimitError"
        rl_results = [r for r in summary.results if r.status == "rate_limited"]
        assert len(rl_results) == 1

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_sync_summary_new_fields_default(self, MockRepo, MockProvider):
        """SyncSummary initializes rate_limited and not_found to 0."""
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = []

        provider = MockProvider.return_value
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:")

        assert summary.rate_limited == 0
        assert summary.not_found == 0

    @patch("src.collectors.sync_collection.MypCardsProvider")
    @patch("src.collectors.sync_collection.Repository")
    async def test_generic_exception_still_caught(self, MockRepo, MockProvider):
        """Generic exceptions are still caught by the fallback handler."""
        rows = [_fake_row(id=1, set_code="dmr", collector_number="123", name_en="Lightning Bolt")]
        repo = MockRepo.return_value
        repo.get_all_collection_entries.return_value = rows

        provider = MockProvider.return_value
        provider.search_card = AsyncMock(return_value=[_search_result()])
        provider.get_card_details = AsyncMock(side_effect=RuntimeError("unexpected error"))
        provider.close = AsyncMock()

        summary = await run_sync_collection(db_url="sqlite:///:memory:", concurrency=1)

        assert len(summary.errors) == 1
        assert summary.errors[0].error_type == "RuntimeError"
        assert summary.not_found == 0
        assert summary.rate_limited == 0

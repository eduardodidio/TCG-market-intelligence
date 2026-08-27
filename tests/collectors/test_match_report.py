"""Tests for the match report orchestrator (F10-T03).

Covers:
 - Summary counts are computed correctly from match results
 - --limit flag restricts number of entries processed
 - Entries without name_en are skipped and counted
 - No DB writes occur (read-only operation)
 - JSON report output is written correctly
 - Error handling when provider.search_card fails
 - format_report produces expected output
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.collection.converter import row_to_collection_entry
from src.collection.matcher import CollectionEntry, MatchResult
from src.collectors.match_report import (
    MatchReportSummary,
    _pct,
    _unmatched_sets,
    format_report,
    run_match_report,
)
from src.domain.models import MypSearchResult

# ── fixtures ────────────────────────────────────────────────────


def _fake_row(
    id: int = 1,
    set_code: str = "dmr",
    collector_number: str = "123",
    name_en: str | None = "Lightning Bolt",
    name_pt: str | None = None,
    user_id: str = "default",
) -> MagicMock:
    """Create a mock UserCollectionRow."""
    row = MagicMock()
    row.id = id
    row.set_code = set_code
    row.collector_number = collector_number
    row.name_en = name_en
    row.name_pt = name_pt
    row.user_id = user_id
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


# ── unit tests: helpers ─────────────────────────────────────────


class TestRowToEntry:
    """row_to_collection_entry correctly converts a DB row to CollectionEntry."""

    def test_converts_row_fields(self):
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


class TestPct:
    """_pct formats percentages correctly."""

    def test_zero_total(self):
        assert _pct(5, 0) == " 0.0%"

    def test_half(self):
        assert _pct(50, 100) == " 50.0%"

    def test_small_fraction(self):
        assert _pct(1, 1000) == "  0.1%"


class TestUnmatchedSets:
    """_unmatched_sets aggregates correctly."""

    def test_counts_unmatched_by_set(self):
        entry_a = CollectionEntry(set_code="dmr", collector_number="1")
        entry_b = CollectionEntry(set_code="dmr", collector_number="2")
        entry_c = CollectionEntry(set_code="ltr", collector_number="1")

        summary = MatchReportSummary(
            results=[
                MatchResult(
                    status="unmatched",
                    collection_entry=entry_a,
                    myp_result=None,
                    confidence="none",
                ),
                MatchResult(
                    status="unmatched",
                    collection_entry=entry_b,
                    myp_result=None,
                    confidence="none",
                ),
                MatchResult(
                    status="matched",
                    collection_entry=entry_c,
                    myp_result=None,
                    confidence="sku_exact",
                ),
            ]
        )

        sets = _unmatched_sets(summary)
        assert sets == [("dmr", 2)]

    def test_empty_results(self):
        summary = MatchReportSummary()
        assert _unmatched_sets(summary) == []


# ── unit tests: format_report ────────────────────────────────────


class TestFormatReport:
    """format_report produces expected text output."""

    def test_basic_report(self):
        summary = MatchReportSummary(
            total=10,
            matched_sku=5,
            matched_name_set=2,
            matched_name_only=2,
            unmatched=1,
        )
        report = format_report(summary)

        assert "=== Collection Match Report ===" in report
        assert "Total collection cards: 10" in report
        assert "Matched (SKU exact)" in report
        assert "Matched (name+set)" in report
        assert "Unmatched" in report

    def test_report_shows_skipped_when_nonzero(self):
        summary = MatchReportSummary(total=5, skipped_no_name=2)
        report = format_report(summary)

        assert "Skipped (no name)" in report

    def test_report_hides_skipped_when_zero(self):
        summary = MatchReportSummary(total=5)
        report = format_report(summary)

        assert "Skipped" not in report

    def test_report_shows_errors_when_nonzero(self):
        summary = MatchReportSummary(total=5, errors=1)
        report = format_report(summary)

        assert "Errors" in report

    def test_report_shows_unmatched_sets(self):
        entry = CollectionEntry(set_code="prm", collector_number="1")
        summary = MatchReportSummary(
            total=1,
            unmatched=1,
            results=[
                MatchResult(
                    status="unmatched",
                    collection_entry=entry,
                    myp_result=None,
                    confidence="none",
                )
            ],
        )
        report = format_report(summary)

        assert "Top unmatched sets:" in report
        assert "prm (1 cards)" in report


class TestMatchedTotal:
    """MatchReportSummary.matched_total property."""

    def test_sums_all_match_types(self):
        s = MatchReportSummary(matched_sku=10, matched_name_set=5, matched_name_only=3)
        assert s.matched_total == 18


# ── integration tests: run_match_report ─────────────────────────


@pytest.mark.asyncio
class TestRunMatchReport:
    """Tests for the async run_match_report orchestrator."""

    @patch("src.collectors.match_report.MypCardsProvider")
    @patch("src.collectors.match_report.Repository")
    async def test_basic_matched_counts(self, MockRepo, MockProvider):
        """SKU-matched entries increment matched_sku."""
        rows = [
            _fake_row(id=1, set_code="dmr", collector_number="123", name_en="Lightning Bolt"),
            _fake_row(id=2, set_code="ltr", collector_number="42", name_en="Gandalf"),
        ]
        MockRepo.return_value.get_all_collection_entries.return_value = rows

        provider_instance = MockProvider.return_value
        provider_instance.search_card = AsyncMock(
            side_effect=[
                [_search_result(set_code="dmr", collector_number="123", name="Lightning Bolt")],
                [
                    _search_result(
                        external_id="2000",
                        set_code="ltr",
                        collector_number="42",
                        name="Gandalf",
                        slug="gandalf",
                    )
                ],
            ]
        )
        provider_instance.close = AsyncMock()

        summary = await run_match_report(db_url="sqlite:///:memory:")

        assert summary.total == 2
        assert summary.matched_sku == 2
        assert summary.unmatched == 0
        assert summary.matched_name_only == 0

    @patch("src.collectors.match_report.MypCardsProvider")
    @patch("src.collectors.match_report.Repository")
    async def test_unmatched_counted(self, MockRepo, MockProvider):
        """Empty search results → unmatched."""
        rows = [_fake_row(id=1, name_en="Obscure Card")]
        MockRepo.return_value.get_all_collection_entries.return_value = rows

        provider_instance = MockProvider.return_value
        provider_instance.search_card = AsyncMock(return_value=[])
        provider_instance.close = AsyncMock()

        summary = await run_match_report(db_url="sqlite:///:memory:")

        assert summary.total == 1
        assert summary.unmatched == 1
        assert summary.matched_sku == 0

    @patch("src.collectors.match_report.MypCardsProvider")
    @patch("src.collectors.match_report.Repository")
    async def test_best_effort_counted_as_name_only(self, MockRepo, MockProvider):
        """Multiple name matches with no SKU → best_effort → name_only."""
        rows = [_fake_row(id=1, set_code="m21", collector_number="152", name_en="Lightning Bolt")]
        MockRepo.return_value.get_all_collection_entries.return_value = rows

        provider_instance = MockProvider.return_value
        provider_instance.search_card = AsyncMock(
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
                    slug="lightning-bolt-2",
                    sku=None,
                    set_code=None,
                    collector_number=None,
                ),
            ]
        )
        provider_instance.close = AsyncMock()

        summary = await run_match_report(db_url="sqlite:///:memory:")

        assert summary.total == 1
        assert summary.matched_name_only == 1
        assert summary.matched_sku == 0

    @patch("src.collectors.match_report.MypCardsProvider")
    @patch("src.collectors.match_report.Repository")
    async def test_limit_restricts_processing(self, MockRepo, MockProvider):
        """--limit flag restricts the number of entries processed."""
        rows = [_fake_row(id=i, name_en=f"Card {i}", collector_number=str(i)) for i in range(1, 11)]
        MockRepo.return_value.get_all_collection_entries.return_value = rows

        provider_instance = MockProvider.return_value
        provider_instance.search_card = AsyncMock(return_value=[])
        provider_instance.close = AsyncMock()

        summary = await run_match_report(db_url="sqlite:///:memory:", limit=3)

        # Total reflects full collection size
        assert summary.total == 10
        # But only 3 were processed (all unmatched since search returns [])
        assert summary.unmatched == 3
        assert provider_instance.search_card.call_count == 3

    @patch("src.collectors.match_report.MypCardsProvider")
    @patch("src.collectors.match_report.Repository")
    async def test_skipped_no_name(self, MockRepo, MockProvider):
        """Entries without name_en are skipped and counted."""
        rows = [
            _fake_row(id=1, name_en=None),
            _fake_row(id=2, name_en="Lightning Bolt"),
        ]
        MockRepo.return_value.get_all_collection_entries.return_value = rows

        provider_instance = MockProvider.return_value
        provider_instance.search_card = AsyncMock(return_value=[])
        provider_instance.close = AsyncMock()

        summary = await run_match_report(db_url="sqlite:///:memory:")

        assert summary.skipped_no_name == 1
        assert summary.unmatched == 1
        # search_card should only be called for the entry WITH a name
        assert provider_instance.search_card.call_count == 1

    @patch("src.collectors.match_report.MypCardsProvider")
    @patch("src.collectors.match_report.Repository")
    async def test_search_error_counted(self, MockRepo, MockProvider):
        """Provider errors are caught and counted."""
        rows = [_fake_row(id=1, name_en="Lightning Bolt")]
        MockRepo.return_value.get_all_collection_entries.return_value = rows

        provider_instance = MockProvider.return_value
        provider_instance.search_card = AsyncMock(side_effect=RuntimeError("timeout"))
        provider_instance.close = AsyncMock()

        summary = await run_match_report(db_url="sqlite:///:memory:")

        assert summary.errors == 1
        assert summary.matched_sku == 0
        assert summary.unmatched == 0

    @patch("src.collectors.match_report.MypCardsProvider")
    @patch("src.collectors.match_report.Repository")
    async def test_no_db_writes(self, MockRepo, MockProvider):
        """The match report is read-only — no DB write methods called."""
        rows = [_fake_row(id=1, name_en="Lightning Bolt")]
        repo_instance = MockRepo.return_value
        repo_instance.get_all_collection_entries.return_value = rows

        provider_instance = MockProvider.return_value
        provider_instance.search_card = AsyncMock(return_value=[_search_result()])
        provider_instance.close = AsyncMock()

        await run_match_report(db_url="sqlite:///:memory:")

        # Verify no write methods were called
        repo_instance.upsert_card.assert_not_called()
        repo_instance.upsert_source_card.assert_not_called()
        repo_instance.insert_price_observations.assert_not_called()
        repo_instance.insert_error.assert_not_called()

    @patch("src.collectors.match_report.MypCardsProvider")
    @patch("src.collectors.match_report.Repository")
    async def test_json_output(self, MockRepo, MockProvider, tmp_path):
        """--output writes a valid JSON report file."""
        rows = [
            _fake_row(id=1, set_code="dmr", collector_number="123", name_en="Lightning Bolt"),
        ]
        MockRepo.return_value.get_all_collection_entries.return_value = rows

        provider_instance = MockProvider.return_value
        provider_instance.search_card = AsyncMock(return_value=[_search_result()])
        provider_instance.close = AsyncMock()

        output_path = str(tmp_path / "report.json")
        await run_match_report(db_url="sqlite:///:memory:", output=output_path)

        assert Path(output_path).exists()
        data = json.loads(Path(output_path).read_text(encoding="utf-8"))

        assert data["total"] == 1
        assert data["matched_sku"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["status"] == "matched"
        assert data["results"][0]["confidence"] == "sku_exact"
        assert data["results"][0]["entry"]["set_code"] == "dmr"
        assert data["results"][0]["myp_match"]["external_id"] == "1000"

    @patch("src.collectors.match_report.MypCardsProvider")
    @patch("src.collectors.match_report.Repository")
    async def test_empty_collection(self, MockRepo, MockProvider):
        """Empty collection produces a valid (zero) report."""
        MockRepo.return_value.get_all_collection_entries.return_value = []

        provider_instance = MockProvider.return_value
        provider_instance.close = AsyncMock()

        summary = await run_match_report(db_url="sqlite:///:memory:")

        assert summary.total == 0
        assert summary.matched_sku == 0
        assert summary.unmatched == 0

    @patch("src.collectors.match_report.MypCardsProvider")
    @patch("src.collectors.match_report.Repository")
    async def test_mixed_results(self, MockRepo, MockProvider):
        """Mixed match results: sku_exact, name_set, unmatched, best_effort."""
        rows = [
            _fake_row(id=1, set_code="dmr", collector_number="123", name_en="Lightning Bolt"),
            _fake_row(id=2, set_code="ltr", collector_number="42", name_en="Gandalf"),
            _fake_row(id=3, set_code="m21", collector_number="99", name_en="Obscure Card"),
            _fake_row(id=4, set_code="neo", collector_number="1", name_en="Duplicate Name"),
        ]
        MockRepo.return_value.get_all_collection_entries.return_value = rows

        provider_instance = MockProvider.return_value
        provider_instance.search_card = AsyncMock(
            side_effect=[
                # Card 1: SKU exact match
                [_search_result(set_code="dmr", collector_number="123", name="Lightning Bolt")],
                # Card 2: name+set match (no SKU)
                [
                    _search_result(
                        external_id="2000",
                        name="Gandalf",
                        slug="gandalf",
                        sku=None,
                        set_code="ltr",
                        collector_number=None,
                    )
                ],
                # Card 3: unmatched (no results)
                [],
                # Card 4: best_effort (multiple name matches, no SKU)
                [
                    _search_result(
                        external_id="4000",
                        name="Duplicate Name",
                        slug="dup1",
                        sku=None,
                        set_code=None,
                        collector_number=None,
                    ),
                    _search_result(
                        external_id="4001",
                        name="Duplicate Name",
                        slug="dup2",
                        sku=None,
                        set_code=None,
                        collector_number=None,
                    ),
                ],
            ]
        )
        provider_instance.close = AsyncMock()

        summary = await run_match_report(db_url="sqlite:///:memory:", concurrency=1)

        assert summary.total == 4
        assert summary.matched_sku == 1
        assert summary.matched_name_set == 1
        assert summary.unmatched == 1
        assert summary.matched_name_only == 1  # best_effort counted as name_only

    @patch("src.collectors.match_report.MypCardsProvider")
    @patch("src.collectors.match_report.Repository")
    async def test_provider_closed_on_success(self, MockRepo, MockProvider):
        """Provider.close() is called even on successful completion."""
        MockRepo.return_value.get_all_collection_entries.return_value = []
        provider_instance = MockProvider.return_value
        provider_instance.close = AsyncMock()

        await run_match_report(db_url="sqlite:///:memory:")

        provider_instance.close.assert_awaited_once()

    @patch("src.collectors.match_report.MypCardsProvider")
    @patch("src.collectors.match_report.Repository")
    async def test_provider_closed_on_error(self, MockRepo, MockProvider):
        """Provider.close() is called even when an error occurs."""
        MockRepo.return_value.get_all_collection_entries.side_effect = RuntimeError("db error")
        provider_instance = MockProvider.return_value
        provider_instance.close = AsyncMock()

        with pytest.raises(RuntimeError, match="db error"):
            await run_match_report(db_url="sqlite:///:memory:")

        provider_instance.close.assert_awaited_once()

    @patch("src.collectors.match_report.MypCardsProvider")
    @patch("src.collectors.match_report.Repository")
    async def test_name_only_match_counted(self, MockRepo, MockProvider):
        """Name-only match (no set match) increments matched_name_only."""
        rows = [
            _fake_row(id=1, set_code="m21", collector_number="152", name_en="Lightning Bolt"),
        ]
        MockRepo.return_value.get_all_collection_entries.return_value = rows

        provider_instance = MockProvider.return_value
        provider_instance.search_card = AsyncMock(
            return_value=[
                _search_result(
                    external_id="9000",
                    name="Lightning Bolt",
                    sku=None,
                    set_code=None,
                    collector_number=None,
                ),
            ]
        )
        provider_instance.close = AsyncMock()

        summary = await run_match_report(db_url="sqlite:///:memory:")

        assert summary.matched_name_only == 1
        assert summary.matched_sku == 0
        assert summary.matched_name_set == 0

"""Tests for backfill collector — concurrency and resume logic."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.models import CardIdentity, SourceCard


def _make_cards(n: int, source: str = "myp") -> list[SourceCard]:
    """Create N fake SourceCard objects."""
    return [
        SourceCard(
            source=source,
            external_id=f"card-{i}",
            url=f"https://example.com/card-{i}",
            sku=f"sku-{i}",
        )
        for i in range(1, n + 1)
    ]


def _make_detailed_card(card: SourceCard) -> SourceCard:
    """Return a card with identity filled in (simulates get_card_details)."""
    return SourceCard(
        source=card.source,
        external_id=card.external_id,
        url=card.url,
        sku=card.sku,
        identity=CardIdentity(
            game="magic",
            name_en=f"Card {card.external_id}",
            set_code="TST",
            collector_number="001",
        ),
    )


@pytest.fixture
def mock_provider():
    """Mock MypCardsProvider with configurable discover/details/history."""
    provider = AsyncMock()
    provider.source_name = "myp"
    provider.discover_cards = AsyncMock(return_value=_make_cards(10))
    provider.get_card_details = AsyncMock(side_effect=lambda c: _make_detailed_card(c))
    provider.get_price_history = AsyncMock(return_value=[])
    provider.close = AsyncMock()
    return provider


@pytest.fixture
def mock_repo():
    """Mock Repository."""
    repo = MagicMock()
    repo.get_cards_with_observations = MagicMock(return_value=[])
    repo.upsert_source_card = MagicMock(return_value=1)
    repo.upsert_card = MagicMock(return_value=1)
    repo.insert_price_observations = MagicMock(return_value=0)
    repo.mark_errors_resolved = MagicMock()
    repo.insert_error = MagicMock()
    return repo


class TestResumeSkip:
    """Resume: skip already-collected cards."""

    @pytest.mark.asyncio
    async def test_resume_skips_collected_cards(self, mock_provider, mock_repo):
        """With resume=True, cards already in DB are skipped."""
        # 5 of 10 cards already collected
        mock_repo.get_cards_with_observations.return_value = [
            (f"card-{i}", 100) for i in range(1, 6)
        ]

        with (
            patch("src.collectors.backfill.MypCardsProvider", return_value=mock_provider),
            patch("src.collectors.backfill.Repository", return_value=mock_repo),
        ):
            from src.collectors.backfill import run_backfill

            summary = await run_backfill(
                db_url="sqlite:///:memory:",
                resume=True,
                concurrency=2,
            )

        assert summary.cards_discovered == 10
        assert summary.cards_processed == 5
        assert summary.cards_failed == 0
        # Only 5 cards processed (card-6 through card-10)
        assert mock_provider.get_card_details.call_count == 5

    @pytest.mark.asyncio
    async def test_no_resume_processes_all(self, mock_provider, mock_repo):
        """With resume=False, all discovered cards are processed."""
        mock_repo.get_cards_with_observations.return_value = [
            (f"card-{i}", 100) for i in range(1, 6)
        ]

        with (
            patch("src.collectors.backfill.MypCardsProvider", return_value=mock_provider),
            patch("src.collectors.backfill.Repository", return_value=mock_repo),
        ):
            from src.collectors.backfill import run_backfill

            summary = await run_backfill(
                db_url="sqlite:///:memory:",
                resume=False,
                concurrency=2,
            )

        assert summary.cards_discovered == 10
        assert summary.cards_processed == 10
        # get_cards_with_observations should not be called when resume=False
        mock_repo.get_cards_with_observations.assert_not_called()


class TestConcurrencyLimit:
    """Verify semaphore limits concurrent processing."""

    @pytest.mark.asyncio
    async def test_concurrency_limits_parallel_execution(self, mock_provider, mock_repo):
        """At most `concurrency` cards should be in-flight simultaneously."""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def tracking_get_details(card):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.01)  # Small delay to overlap
            result = _make_detailed_card(card)
            async with lock:
                current_concurrent -= 1
            return result

        mock_provider.get_card_details = AsyncMock(side_effect=tracking_get_details)

        with (
            patch("src.collectors.backfill.MypCardsProvider", return_value=mock_provider),
            patch("src.collectors.backfill.Repository", return_value=mock_repo),
        ):
            from src.collectors.backfill import run_backfill

            summary = await run_backfill(
                db_url="sqlite:///:memory:",
                resume=False,
                concurrency=2,
            )

        assert summary.cards_processed == 10
        assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_concurrency_default_is_3(self):
        """Default concurrency parameter is 3."""
        import inspect

        from src.collectors.backfill import run_backfill

        sig = inspect.signature(run_backfill)
        assert sig.parameters["concurrency"].default == 3


class TestErrorIsolation:
    """Individual card failures must not crash the batch."""

    @pytest.mark.asyncio
    async def test_one_failure_does_not_crash_batch(self, mock_provider, mock_repo):
        """If one card raises an exception, others still complete."""
        call_count = 0

        async def failing_get_details(card):
            nonlocal call_count
            call_count += 1
            if card.external_id == "card-3":
                raise RuntimeError("Network error on card-3")
            return _make_detailed_card(card)

        mock_provider.get_card_details = AsyncMock(side_effect=failing_get_details)

        with (
            patch("src.collectors.backfill.MypCardsProvider", return_value=mock_provider),
            patch("src.collectors.backfill.Repository", return_value=mock_repo),
        ):
            from src.collectors.backfill import run_backfill

            summary = await run_backfill(
                db_url="sqlite:///:memory:",
                resume=False,
                concurrency=3,
            )

        assert summary.cards_processed == 9
        assert summary.cards_failed == 1
        assert len(summary.errors) == 1
        assert summary.errors[0].external_id == "card-3"
        assert summary.errors[0].error_type == "RuntimeError"

    @pytest.mark.asyncio
    async def test_multiple_failures_all_isolated(self, mock_provider, mock_repo):
        """Multiple cards can fail independently."""
        failing_ids = {"card-2", "card-5", "card-8"}

        async def multi_fail_details(card):
            if card.external_id in failing_ids:
                raise ValueError(f"Failed: {card.external_id}")
            return _make_detailed_card(card)

        mock_provider.get_card_details = AsyncMock(side_effect=multi_fail_details)

        with (
            patch("src.collectors.backfill.MypCardsProvider", return_value=mock_provider),
            patch("src.collectors.backfill.Repository", return_value=mock_repo),
        ):
            from src.collectors.backfill import run_backfill

            summary = await run_backfill(
                db_url="sqlite:///:memory:",
                resume=False,
                concurrency=2,
            )

        assert summary.cards_processed == 7
        assert summary.cards_failed == 3
        failed_ids = {e.external_id for e in summary.errors}
        assert failed_ids == failing_ids


class TestEmptyDiscovery:
    """Discover 0 cards — clean exit."""

    @pytest.mark.asyncio
    async def test_empty_discovery_returns_clean_summary(self, mock_provider, mock_repo):
        """Zero discovered cards produces a valid summary with no errors."""
        mock_provider.discover_cards = AsyncMock(return_value=[])

        with (
            patch("src.collectors.backfill.MypCardsProvider", return_value=mock_provider),
            patch("src.collectors.backfill.Repository", return_value=mock_repo),
        ):
            from src.collectors.backfill import run_backfill

            summary = await run_backfill(
                db_url="sqlite:///:memory:",
                resume=True,
                concurrency=3,
            )

        assert summary.cards_discovered == 0
        assert summary.cards_processed == 0
        assert summary.cards_failed == 0
        assert summary.finished_at is not None


class TestDryRunResume:
    """Dry run + resume: resume is effectively ignored."""

    @pytest.mark.asyncio
    async def test_dry_run_skips_resume_check(self, mock_provider):
        """In dry_run mode, no repo is created so resume has no effect."""
        mock_provider.discover_cards = AsyncMock(return_value=_make_cards(3))

        with patch("src.collectors.backfill.MypCardsProvider", return_value=mock_provider):
            from src.collectors.backfill import run_backfill

            summary = await run_backfill(
                db_url="sqlite:///:memory:",
                dry_run=True,
                resume=True,
                concurrency=2,
            )

        # All 3 cards processed (no DB to check for resume)
        assert summary.cards_discovered == 3
        assert summary.cards_processed == 3


class TestSummaryAccuracy:
    """Summary counts must be accurate."""

    @pytest.mark.asyncio
    async def test_summary_counts_with_resume_and_failures(self, mock_provider, mock_repo):
        """discovered = total found, processed + failed = remaining after resume."""
        # 3 already collected
        mock_repo.get_cards_with_observations.return_value = [
            ("card-1", 50),
            ("card-2", 50),
            ("card-3", 50),
        ]

        # card-5 will fail
        async def partial_fail(card):
            if card.external_id == "card-5":
                raise RuntimeError("fail")
            return _make_detailed_card(card)

        mock_provider.get_card_details = AsyncMock(side_effect=partial_fail)

        with (
            patch("src.collectors.backfill.MypCardsProvider", return_value=mock_provider),
            patch("src.collectors.backfill.Repository", return_value=mock_repo),
        ):
            from src.collectors.backfill import run_backfill

            summary = await run_backfill(
                db_url="sqlite:///:memory:",
                resume=True,
                concurrency=2,
            )

        assert summary.cards_discovered == 10  # total found
        assert summary.cards_processed == 6  # 7 remaining - 1 failed
        assert summary.cards_failed == 1
        assert summary.cards_processed + summary.cards_failed == 7  # remaining after skip

    @pytest.mark.asyncio
    async def test_finished_at_is_set(self, mock_provider, mock_repo):
        """finished_at is always set after processing."""
        with (
            patch("src.collectors.backfill.MypCardsProvider", return_value=mock_provider),
            patch("src.collectors.backfill.Repository", return_value=mock_repo),
        ):
            from src.collectors.backfill import run_backfill

            summary = await run_backfill(
                db_url="sqlite:///:memory:",
                resume=False,
                concurrency=3,
            )

        assert summary.finished_at is not None


class TestProgressLogging:
    """Progress logging emits structured log events."""

    @pytest.mark.asyncio
    async def test_processing_card_log_emitted(self, mock_provider, mock_repo):
        """Each card emits a processing_card log with index and total."""
        mock_provider.discover_cards = AsyncMock(return_value=_make_cards(2))

        with (
            patch("src.collectors.backfill.MypCardsProvider", return_value=mock_provider),
            patch("src.collectors.backfill.Repository", return_value=mock_repo),
            patch("src.collectors.backfill.log") as mock_log,
        ):
            from src.collectors.backfill import run_backfill

            await run_backfill(
                db_url="sqlite:///:memory:",
                resume=False,
                concurrency=1,
            )

        # Find all processing_card calls
        processing_calls = [
            call
            for call in mock_log.info.call_args_list
            if call.args and call.args[0] == "processing_card"
        ]
        assert len(processing_calls) == 2
        # Verify index and total kwargs
        assert processing_calls[0].kwargs["index"] in (1, 2)
        assert processing_calls[0].kwargs["total"] == 2

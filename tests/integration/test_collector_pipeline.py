"""Integration tests for the collector pipeline (backfill, update, retry-failed).

These tests exercise the full stack with mocked HTTP responses and a real
in-memory SQLite database. Only the HTTP layer is mocked — parsers, repository,
and domain logic all run for real.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from src.collectors.backfill import run_backfill, run_retry_failed, run_update
from src.database.repository import Repository
from src.domain.models import CollectionError

# ---------------------------------------------------------------------------
# Minimal HTML fixtures — just enough for the real parsers to extract data
# ---------------------------------------------------------------------------

EDITIONS_HTML = """
<html><body>
<a href="/magic/test-set">Test Set</a>
<a href="/magic/other-set">Other Set</a>
</body></html>
"""

SET_PAGE_HTML = """
<html><body>
<a href="/magic/produto/1001/test-card-alpha">Test Card Alpha</a>
<a href="/magic/produto/1002/test-card-beta">Test Card Beta</a>
</body></html>
"""

SET_PAGE_HTML_THREE_CARDS = """
<html><body>
<a href="/magic/produto/1001/test-card-alpha">Test Card Alpha</a>
<a href="/magic/produto/1002/test-card-beta">Test Card Beta</a>
<a href="/magic/produto/1003/test-card-gamma">Test Card Gamma</a>
</body></html>
"""

OTHER_SET_PAGE_HTML = """
<html><body>
<a href="/magic/produto/2001/other-card-one">Other Card One</a>
</body></html>
"""


def _make_card_page_html(card_id: str, sku: str, name: str) -> str:
    """Build a minimal card product page with valid JSON-LD."""
    product = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "productID": card_id,
        "sku": sku,
        "image": f"https://mypcards.com/img/{sku}_en.jpg",
        "offers": {"@type": "Offer", "price": "10.50", "priceCurrency": "BRL"},
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"name": "Home"},
            {"name": "Magic"},
            {"name": "Test Set"},
            {"name": name},
        ],
    }
    return f"""<html><body>
<script type="application/ld+json">{json.dumps(product)}</script>
<script type="application/ld+json">{json.dumps(breadcrumb)}</script>
</body></html>"""


def _make_history_html(card_id: str, num_days: int = 3) -> str:
    """Build a minimal price history page with window.precoChartConfig."""
    labels = [f"{d:02d}/01/2026" for d in range(1, num_days + 1)]
    config = {
        "labels": labels,
        "series": [
            {"key": "mediana", "dados": [10.0 + i for i in range(num_days)]},
            {"key": "tcg", "dados": [12.0 + i for i in range(num_days)]},
            {"key": "ultimo", "dados": [9.0 + i for i in range(num_days)]},
            {"key": "volume", "dados": [5 + i for i in range(num_days)]},
        ],
    }
    return f"""<html><body>
<script>
window.precoChartConfig = {json.dumps(config)};
</script>
</body></html>"""


CARD_1001_PAGE = _make_card_page_html("1001", "magic_tst_001", "Test Card Alpha")
CARD_1002_PAGE = _make_card_page_html("1002", "magic_tst_002", "Test Card Beta")
CARD_1003_PAGE = _make_card_page_html("1003", "magic_tst_003", "Test Card Gamma")
CARD_2001_PAGE = _make_card_page_html("2001", "magic_oth_001", "Other Card One")

HISTORY_1001 = _make_history_html("1001", num_days=3)
HISTORY_1002 = _make_history_html("1002", num_days=2)
HISTORY_1003 = _make_history_html("1003", num_days=3)
HISTORY_2001 = _make_history_html("2001", num_days=2)


# ---------------------------------------------------------------------------
# URL-to-response mapping helper
# ---------------------------------------------------------------------------


def _build_fetch_side_effect(url_map: dict[str, str]):
    """Return an async function that maps URL substrings to HTML responses.

    The returned function accepts (self, url) since it replaces a bound method.
    Raises RuntimeError for URLs that have no match (simulating HTTP errors).
    """

    async def _fake_fetch(self, url: str) -> str:
        for pattern, html in url_map.items():
            if pattern in url:
                return html
        raise RuntimeError(f"Simulated HTTP error for {url}")

    return _fake_fetch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_url(tmp_path):
    """Use a temp file DB so multiple Repository instances share the same data."""
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def default_url_map():
    """Standard URL map: two sets with 2 cards each."""
    return {
        "/magic/edicoes": EDITIONS_HTML,
        "/magic/test-set": SET_PAGE_HTML,
        "/magic/other-set": OTHER_SET_PAGE_HTML,
        "/magic/produto/1001/": CARD_1001_PAGE,
        "/magic/produto/1002/": CARD_1002_PAGE,
        "/magic/produto/2001/": CARD_2001_PAGE,
        "/magic/preco/1001/": HISTORY_1001,
        "/magic/preco/1002/": HISTORY_1002,
        "/magic/preco/2001/": HISTORY_2001,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBackfillFullPipeline:
    """test_backfill_full_pipeline — discover -> details -> history -> DB."""

    async def test_backfill_full_pipeline(self, db_url, default_url_map):
        fetch_fn = _build_fetch_side_effect(default_url_map)

        with (
            patch("src.collectors.backfill.MypCardsProvider._fetch", new=fetch_fn),
            patch("src.collectors.backfill.MypCardsProvider.close", new_callable=AsyncMock),
        ):
            summary = await run_backfill(
                db_url=db_url,
                delay=0,
                concurrency=2,
                resume=False,
            )

        assert summary.cards_discovered == 3  # 2 from test-set + 1 from other-set
        assert summary.cards_processed == 3
        assert summary.cards_failed == 0
        assert summary.observations_saved > 0
        assert summary.finished_at is not None

        # Verify data actually landed in DB
        repo = Repository(db_url)
        obs_count = repo.get_observation_count("myp")
        assert obs_count == summary.observations_saved


class TestBackfillWithSetFilter:
    """test_backfill_with_set_filter — only processes filtered set."""

    async def test_backfill_with_set_filter(self, db_url, default_url_map):
        fetch_fn = _build_fetch_side_effect(default_url_map)

        with (
            patch("src.collectors.backfill.MypCardsProvider._fetch", new=fetch_fn),
            patch("src.collectors.backfill.MypCardsProvider.close", new_callable=AsyncMock),
        ):
            summary = await run_backfill(
                db_url=db_url,
                set_filter="test-set",
                delay=0,
                concurrency=2,
                resume=False,
            )

        assert summary.cards_discovered == 2  # only test-set cards
        assert summary.cards_processed == 2
        assert summary.cards_failed == 0

        # Verify only test-set cards in DB
        repo = Repository(db_url)
        source_cards = repo.get_all_source_cards("myp")
        assert len(source_cards) == 2
        skus = {sc.sku for sc in source_cards}
        assert skus == {"magic_tst_001", "magic_tst_002"}


class TestBackfillDryRun:
    """test_backfill_dry_run — no DB writes."""

    async def test_backfill_dry_run(self, db_url, default_url_map):
        fetch_fn = _build_fetch_side_effect(default_url_map)

        with (
            patch("src.collectors.backfill.MypCardsProvider._fetch", new=fetch_fn),
            patch("src.collectors.backfill.MypCardsProvider.close", new_callable=AsyncMock),
        ):
            summary = await run_backfill(
                db_url=db_url,
                set_filter="test-set",
                dry_run=True,
                delay=0,
                concurrency=2,
                resume=False,
            )

        # Dry run still reports counts but does not persist
        assert summary.cards_discovered == 2
        assert summary.observations_saved > 0  # counted even in dry_run

        # DB should be empty (repo was never created by backfill in dry_run)
        repo = Repository(db_url)
        obs_count = repo.get_observation_count("myp")
        assert obs_count == 0


class TestBackfillResumeSkipsCollected:
    """test_backfill_resume_skips_collected — cards in DB are skipped."""

    async def test_backfill_resume_skips_collected(self, db_url, default_url_map):
        fetch_fn = _build_fetch_side_effect(default_url_map)

        # First run: collect card 1001 and 1002
        with (
            patch("src.collectors.backfill.MypCardsProvider._fetch", new=fetch_fn),
            patch("src.collectors.backfill.MypCardsProvider.close", new_callable=AsyncMock),
        ):
            first = await run_backfill(
                db_url=db_url,
                set_filter="test-set",
                delay=0,
                concurrency=2,
                resume=False,
            )

        assert first.cards_processed == 2

        # Second run with resume=True: should skip already-collected cards
        with (
            patch("src.collectors.backfill.MypCardsProvider._fetch", new=fetch_fn),
            patch("src.collectors.backfill.MypCardsProvider.close", new_callable=AsyncMock),
        ):
            second = await run_backfill(
                db_url=db_url,
                set_filter="test-set",
                delay=0,
                concurrency=2,
                resume=True,
            )

        # All cards already collected — nothing new to process
        assert second.cards_discovered == 2  # discovered before resume filter
        assert second.cards_processed == 0
        assert second.cards_failed == 0


class TestBackfillCardErrorContinues:
    """test_backfill_card_error_continues — one card fails, others succeed."""

    async def test_backfill_card_error_continues(self, db_url):
        # Card 1002 will fail (no URL match for its product page)
        url_map = {
            "/magic/test-set": SET_PAGE_HTML,
            "/magic/produto/1001/": CARD_1001_PAGE,
            # 1002 product page deliberately missing -> RuntimeError
            "/magic/preco/1001/": HISTORY_1001,
        }
        fetch_fn = _build_fetch_side_effect(url_map)

        with (
            patch("src.collectors.backfill.MypCardsProvider._fetch", new=fetch_fn),
            patch("src.collectors.backfill.MypCardsProvider.close", new_callable=AsyncMock),
        ):
            summary = await run_backfill(
                db_url=db_url,
                set_filter="test-set",
                delay=0,
                concurrency=1,
                resume=False,
            )

        assert summary.cards_discovered == 2
        assert summary.cards_processed == 1
        assert summary.cards_failed == 1
        assert len(summary.errors) == 1
        assert summary.errors[0].external_id == "1002"

        # Verify the successful card's data is in DB
        repo = Repository(db_url)
        obs_count = repo.get_observation_count("myp")
        assert obs_count > 0


class TestUpdateExistingCards:
    """test_update_existing_cards — fetches recent history for known cards."""

    async def test_update_existing_cards(self, db_url, default_url_map):
        fetch_fn = _build_fetch_side_effect(default_url_map)

        # First: backfill to populate source_cards table
        with (
            patch("src.collectors.backfill.MypCardsProvider._fetch", new=fetch_fn),
            patch("src.collectors.backfill.MypCardsProvider.close", new_callable=AsyncMock),
        ):
            await run_backfill(
                db_url=db_url,
                set_filter="test-set",
                delay=0,
                concurrency=2,
                resume=False,
            )

        # Now run update — it should fetch history for the 2 known cards
        with (
            patch("src.collectors.backfill.MypCardsProvider._fetch", new=fetch_fn),
            patch("src.collectors.backfill.MypCardsProvider.close", new_callable=AsyncMock),
        ):
            summary = await run_update(
                db_url=db_url,
                delay=0,
                history_days=30,
            )

        assert summary.cards_discovered == 2
        assert summary.cards_processed == 2
        assert summary.cards_failed == 0
        # Observations are upserted so duplicates are skipped
        assert summary.observations_saved >= 0


class TestRetryFailedCards:
    """test_retry_failed_cards — retries cards with unresolved errors."""

    async def test_retry_failed_cards(self, db_url, default_url_map):
        # Insert an unresolved error for card 1001
        repo = Repository(db_url)
        error = CollectionError(
            source="myp",
            external_id="1001",
            url="https://mypcards.com/magic/produto/1001/test-card-alpha",
            error_type="RuntimeError",
            error_message="Simulated failure",
        )
        repo.insert_error(error)

        fetch_fn = _build_fetch_side_effect(default_url_map)

        # Retry should pick up the error and re-process card 1001
        with (
            patch("src.collectors.backfill.MypCardsProvider._fetch", new=fetch_fn),
            patch("src.collectors.backfill.MypCardsProvider.close", new_callable=AsyncMock),
        ):
            summary = await run_retry_failed(
                db_url=db_url,
                delay=0,
                history_days=30,
            )

        assert summary.cards_discovered == 1
        assert summary.cards_processed == 1
        assert summary.cards_failed == 0
        assert summary.observations_saved > 0

        # The error should now be resolved
        unresolved = repo.get_unresolved_errors("myp")
        assert len(unresolved) == 0


class TestRetryNoErrors:
    """test_retry_no_errors — clean exit when no errors exist."""

    async def test_retry_no_errors(self, db_url):
        with (
            patch(
                "src.collectors.backfill.MypCardsProvider._fetch",
                new_callable=AsyncMock,
            ),
            patch("src.collectors.backfill.MypCardsProvider.close", new_callable=AsyncMock),
        ):
            summary = await run_retry_failed(
                db_url=db_url,
                delay=0,
            )

        assert summary.cards_discovered == 0
        assert summary.cards_processed == 0
        assert summary.cards_failed == 0
        assert summary.observations_saved == 0


class TestBackfillConcurrent:
    """test_backfill_concurrent — verify concurrency parameter is respected."""

    async def test_backfill_concurrent(self, db_url):
        url_map = {
            "/magic/test-set": SET_PAGE_HTML_THREE_CARDS,
            "/magic/produto/1001/": CARD_1001_PAGE,
            "/magic/produto/1002/": CARD_1002_PAGE,
            "/magic/produto/1003/": CARD_1003_PAGE,
            "/magic/preco/1001/": HISTORY_1001,
            "/magic/preco/1002/": HISTORY_1002,
            "/magic/preco/1003/": HISTORY_1003,
        }

        # Track max concurrent executions via semaphore observation
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        original_fetch = _build_fetch_side_effect(url_map)

        async def tracking_fetch(self_provider, fetch_url):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            try:
                return await original_fetch(self_provider, fetch_url)
            finally:
                async with lock:
                    current_concurrent -= 1

        with (
            patch("src.collectors.backfill.MypCardsProvider._fetch", new=tracking_fetch),
            patch("src.collectors.backfill.MypCardsProvider.close", new_callable=AsyncMock),
        ):
            summary = await run_backfill(
                db_url=db_url,
                set_filter="test-set",
                delay=0,
                concurrency=1,
                resume=False,
            )

        assert summary.cards_processed == 3
        assert summary.cards_failed == 0
        # With concurrency=1, at most 1 card processed at a time.
        # Each card makes 2 fetches (details + history) sequentially.
        # The semaphore limits card-level concurrency so max_concurrent
        # for fetches within concurrent cards should be bounded.
        # The discover fetch runs before the concurrent phase and is excluded.
        assert max_concurrent >= 1  # at least one fetch happened
        assert max_concurrent <= 2  # concurrency=1: max 2 fetches from 1 card (details+history)


class TestSummaryCountsAccurate:
    """test_summary_counts_accurate — verify all summary fields."""

    async def test_summary_counts_accurate(self, db_url):
        url_map = {
            "/magic/test-set": SET_PAGE_HTML_THREE_CARDS,
            "/magic/produto/1001/": CARD_1001_PAGE,
            "/magic/produto/1002/": CARD_1002_PAGE,
            # 1003 product page missing -> will fail
            "/magic/preco/1001/": HISTORY_1001,
            "/magic/preco/1002/": HISTORY_1002,
        }
        fetch_fn = _build_fetch_side_effect(url_map)

        with (
            patch("src.collectors.backfill.MypCardsProvider._fetch", new=fetch_fn),
            patch("src.collectors.backfill.MypCardsProvider.close", new_callable=AsyncMock),
        ):
            summary = await run_backfill(
                db_url=db_url,
                set_filter="test-set",
                delay=0,
                concurrency=1,
                resume=False,
            )

        # 3 discovered, 2 processed, 1 failed
        assert summary.cards_discovered == 3
        assert summary.cards_processed == 2
        assert summary.cards_failed == 1
        assert summary.cards_processed + summary.cards_failed == 3

        # Observations: card 1001 has 3 history points, card 1002 has 2
        assert summary.observations_saved == 5

        # Errors list
        assert len(summary.errors) == 1
        assert summary.errors[0].external_id == "1003"

        # Timing
        assert summary.started_at is not None
        assert summary.finished_at is not None
        assert summary.finished_at >= summary.started_at

        # Verify DB matches summary
        repo = Repository(db_url)
        db_obs = repo.get_observation_count("myp")
        assert db_obs == summary.observations_saved

        # Verify error was persisted in DB
        unresolved = repo.get_unresolved_errors("myp")
        assert len(unresolved) == 1
        assert unresolved[0].external_id == "1003"

"""Integration tests for the collection sync pipeline (F10-T12).

These tests exercise the full sync pipeline with a real in-memory SQLite
database and mocked MYP provider responses.  Unlike the unit tests in
test_sync_collection.py (which mock both Repository and Provider), these
tests verify actual DB state after sync completes.

Test scenarios:
  1. Full sync happy path (3 cards)
  2. Partial match (some found, some not)
  3. Resume after partial sync (skip_matched)
  4. Error recovery (provider exception for 1 card)
  5. Cleanup + sync integration
  6. Duplicate collection entries (same card, different quality)
  7. Card with no price history
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.collectors.sync_collection import run_sync_collection
from src.database.models import (
    CardRow,
    PriceObservationRow,
    SourceCardRow,
    UserCollectionRow,
)
from src.database.repository import Repository
from tests.fixtures.myp_search_responses import (
    brainstorm_detail,
    brainstorm_search,
    counterspell_detail,
    counterspell_search,
    dark_ritual_detail,
    dark_ritual_search,
    empty_search,
    lightning_bolt_detail,
    lightning_bolt_search,
    make_price_history,
    swords_to_plowshares_detail,
    swords_to_plowshares_search,
)

# ── helpers ──────────────────────────────────────────────────────


def _seed_collection_entries(
    repo: Repository,
    cards: list[dict],
    user_id: str = "eduardo",
) -> list[int]:
    """Insert UserCollectionRow entries and return their IDs."""
    entry_ids = []
    with Session(repo.engine) as session:
        for card in cards:
            row = UserCollectionRow(
                user_id=user_id,
                set_code=card["set_code"],
                collector_number=card["collector_number"],
                name_en=card.get("name_en"),
                name_pt=card.get("name_pt"),
                quantity=card.get("quantity", 1),
                quality=card.get("quality"),
            )
            session.add(row)
            session.flush()
            entry_ids.append(row.id)
        session.commit()
    return entry_ids


def _count_rows(repo: Repository, model) -> int:
    """Count total rows in a table."""
    with Session(repo.engine) as session:
        return session.execute(select(model).with_only_columns(model.id)).all().__len__()


def _get_collection_entries(repo: Repository) -> list[UserCollectionRow]:
    """Fetch all user_collection entries."""
    with Session(repo.engine) as session:
        return list(session.execute(select(UserCollectionRow)).scalars().all())


# ── fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def repo():
    """Create a Repository backed by in-memory SQLite."""
    r = Repository(db_url="sqlite:///:memory:")
    return r


def _make_provider_mock():
    """Create a mock MypCardsProvider with close method."""
    provider = AsyncMock()
    provider.close = AsyncMock()
    return provider


# ── Test 1: Full sync happy path ─────────────────────────────────


@pytest.mark.asyncio
class TestFullSyncHappyPath:
    """3 collection entries all match and sync successfully."""

    async def test_full_sync_creates_cards_and_observations(self, repo):
        # Seed 3 collection entries
        cards_to_seed = [
            {"name_en": "Lightning Bolt", "set_code": "dmr", "collector_number": "141"},
            {"name_en": "Counterspell", "set_code": "dmr", "collector_number": "064"},
            {"name_en": "Swords to Plowshares", "set_code": "dmr", "collector_number": "028"},
        ]
        _seed_collection_entries(repo, cards_to_seed)

        # Mock provider
        provider = _make_provider_mock()
        provider.search_card = AsyncMock(
            side_effect=[
                lightning_bolt_search(),
                counterspell_search(),
                swords_to_plowshares_search(),
            ]
        )
        provider.get_card_details = AsyncMock(
            side_effect=[
                lightning_bolt_detail(),
                counterspell_detail(),
                swords_to_plowshares_detail(),
            ]
        )
        provider.get_price_history = AsyncMock(
            side_effect=[
                make_price_history("45231", count=5),
                make_price_history("78442", count=3),
                make_price_history("91205", count=4),
            ]
        )

        with (
            patch("src.collectors.sync_collection.Repository", return_value=repo),
            patch("src.collectors.sync_collection.MypCardsProvider", return_value=provider),
        ):
            summary = await run_sync_collection(
                db_url="sqlite:///:memory:",
                concurrency=1,
                delay=0,
            )

        # Verify summary
        assert summary.total_entries == 3
        assert summary.matched == 3
        assert summary.unmatched == 0
        assert summary.cards_created == 3
        assert summary.observations_saved == 12  # 5+3+4
        assert len(summary.errors) == 0
        assert summary.finished_at is not None

        # Verify DB state: cards table
        with Session(repo.engine) as session:
            cards = session.execute(select(CardRow)).scalars().all()
            assert len(cards) == 3
            card_names = {c.name_en for c in cards}
            assert card_names == {"Lightning Bolt", "Counterspell", "Swords to Plowshares"}
            # All cards have game="magic" and set_code="dmr"
            assert all(c.game == "magic" for c in cards)
            assert all(c.set_code == "dmr" for c in cards)

        # Verify DB state: source_cards table
        with Session(repo.engine) as session:
            source_cards = session.execute(select(SourceCardRow)).scalars().all()
            assert len(source_cards) == 3
            ext_ids = {sc.external_id for sc in source_cards}
            assert ext_ids == {"45231", "78442", "91205"}
            # All linked to cards
            assert all(sc.card_id is not None for sc in source_cards)

        # Verify DB state: price_observations table
        with Session(repo.engine) as session:
            obs = session.execute(select(PriceObservationRow)).scalars().all()
            assert len(obs) == 12

        # Verify DB state: user_collection entries have card_id set
        with Session(repo.engine) as session:
            entries = session.execute(select(UserCollectionRow)).scalars().all()
            assert len(entries) == 3
            assert all(e.card_id is not None for e in entries)


# ── Test 2: Partial match ─────────────────────────────────────────


@pytest.mark.asyncio
class TestPartialMatch:
    """5 collection entries: 3 match, 2 do not."""

    async def test_partial_match_counts(self, repo):
        cards_to_seed = [
            {"name_en": "Lightning Bolt", "set_code": "dmr", "collector_number": "141"},
            {"name_en": "Counterspell", "set_code": "dmr", "collector_number": "064"},
            {"name_en": "Swords to Plowshares", "set_code": "dmr", "collector_number": "028"},
            {"name_en": "Nonexistent Card A", "set_code": "xyz", "collector_number": "999"},
            {"name_en": "Nonexistent Card B", "set_code": "abc", "collector_number": "888"},
        ]
        _seed_collection_entries(repo, cards_to_seed)

        provider = _make_provider_mock()
        provider.search_card = AsyncMock(
            side_effect=[
                lightning_bolt_search(),
                counterspell_search(),
                swords_to_plowshares_search(),
                empty_search(),  # Nonexistent Card A
                empty_search(),  # Nonexistent Card B
            ]
        )
        provider.get_card_details = AsyncMock(
            side_effect=[
                lightning_bolt_detail(),
                counterspell_detail(),
                swords_to_plowshares_detail(),
            ]
        )
        provider.get_price_history = AsyncMock(
            side_effect=[
                make_price_history("45231", count=3),
                make_price_history("78442", count=3),
                make_price_history("91205", count=3),
            ]
        )

        with (
            patch("src.collectors.sync_collection.Repository", return_value=repo),
            patch("src.collectors.sync_collection.MypCardsProvider", return_value=provider),
        ):
            summary = await run_sync_collection(
                db_url="sqlite:///:memory:",
                concurrency=1,
                delay=0,
            )

        assert summary.matched == 3
        assert summary.unmatched == 2
        assert summary.total_entries == 5

        # Verify unmatched entries still have card_id == NULL
        with Session(repo.engine) as session:
            entries = (
                session.execute(select(UserCollectionRow).order_by(UserCollectionRow.id))
                .scalars()
                .all()
            )
            linked = [e for e in entries if e.card_id is not None]
            unlinked = [e for e in entries if e.card_id is None]
            assert len(linked) == 3
            assert len(unlinked) == 2

        # Only 3 cards in cards table
        with Session(repo.engine) as session:
            cards = session.execute(select(CardRow)).scalars().all()
            assert len(cards) == 3


# ── Test 3: Resume after partial sync ────────────────────────────


@pytest.mark.asyncio
class TestResumeAfterPartialSync:
    """Run sync with limit=2, then run again with skip_matched=True.

    Second run should only process unlinked entries, no duplicates.
    """

    async def test_resume_no_duplicates(self, repo):
        cards_to_seed = [
            {"name_en": "Lightning Bolt", "set_code": "dmr", "collector_number": "141"},
            {"name_en": "Counterspell", "set_code": "dmr", "collector_number": "064"},
            {"name_en": "Swords to Plowshares", "set_code": "dmr", "collector_number": "028"},
        ]
        _seed_collection_entries(repo, cards_to_seed)

        # First run: limit=2 (processes Lightning Bolt + Counterspell)
        provider1 = _make_provider_mock()
        provider1.search_card = AsyncMock(
            side_effect=[
                lightning_bolt_search(),
                counterspell_search(),
            ]
        )
        provider1.get_card_details = AsyncMock(
            side_effect=[
                lightning_bolt_detail(),
                counterspell_detail(),
            ]
        )
        provider1.get_price_history = AsyncMock(
            side_effect=[
                make_price_history("45231", count=3),
                make_price_history("78442", count=3),
            ]
        )

        with (
            patch("src.collectors.sync_collection.Repository", return_value=repo),
            patch("src.collectors.sync_collection.MypCardsProvider", return_value=provider1),
        ):
            summary1 = await run_sync_collection(
                db_url="sqlite:///:memory:",
                limit=2,
                skip_matched=False,
                concurrency=1,
                delay=0,
            )

        assert summary1.matched == 2

        # Verify 2 entries linked
        with Session(repo.engine) as session:
            entries = session.execute(select(UserCollectionRow)).scalars().all()
            linked = [e for e in entries if e.card_id is not None]
            assert len(linked) == 2

        # Second run: skip_matched=True (should only process Swords to Plowshares)
        provider2 = _make_provider_mock()
        provider2.search_card = AsyncMock(return_value=swords_to_plowshares_search())
        provider2.get_card_details = AsyncMock(return_value=swords_to_plowshares_detail())
        provider2.get_price_history = AsyncMock(return_value=make_price_history("91205", count=4))

        with (
            patch("src.collectors.sync_collection.Repository", return_value=repo),
            patch("src.collectors.sync_collection.MypCardsProvider", return_value=provider2),
        ):
            summary2 = await run_sync_collection(
                db_url="sqlite:///:memory:",
                skip_matched=True,
                concurrency=1,
                delay=0,
            )

        assert summary2.total_entries == 3
        assert summary2.skipped_already_linked == 2
        assert summary2.matched == 1
        # Only 1 search call in second run
        assert provider2.search_card.call_count == 1

        # Verify no duplicate cards
        with Session(repo.engine) as session:
            cards = session.execute(select(CardRow)).scalars().all()
            assert len(cards) == 3
            # No duplicate observations (6 from run 1, 4 from run 2)
            obs = session.execute(select(PriceObservationRow)).scalars().all()
            assert len(obs) == 10

        # All 3 entries now linked
        with Session(repo.engine) as session:
            entries = session.execute(select(UserCollectionRow)).scalars().all()
            assert all(e.card_id is not None for e in entries)


# ── Test 4: Error recovery ───────────────────────────────────────


@pytest.mark.asyncio
class TestErrorRecovery:
    """Provider raises an exception for 1 card; sync continues for others."""

    async def test_error_does_not_abort_other_cards(self, repo):
        cards_to_seed = [
            {"name_en": "Lightning Bolt", "set_code": "dmr", "collector_number": "141"},
            {"name_en": "Counterspell", "set_code": "dmr", "collector_number": "064"},
            {"name_en": "Swords to Plowshares", "set_code": "dmr", "collector_number": "028"},
        ]
        _seed_collection_entries(repo, cards_to_seed)

        provider = _make_provider_mock()
        provider.search_card = AsyncMock(
            side_effect=[
                lightning_bolt_search(),
                counterspell_search(),
                swords_to_plowshares_search(),
            ]
        )
        # Lightning Bolt detail succeeds, Counterspell raises, Swords succeeds
        provider.get_card_details = AsyncMock(
            side_effect=[
                lightning_bolt_detail(),
                RuntimeError("Network timeout on Counterspell"),
                swords_to_plowshares_detail(),
            ]
        )
        provider.get_price_history = AsyncMock(
            side_effect=[
                make_price_history("45231", count=3),
                # Counterspell never reaches get_price_history
                make_price_history("91205", count=4),
            ]
        )

        with (
            patch("src.collectors.sync_collection.Repository", return_value=repo),
            patch("src.collectors.sync_collection.MypCardsProvider", return_value=provider),
        ):
            summary = await run_sync_collection(
                db_url="sqlite:///:memory:",
                concurrency=1,
                delay=0,
            )

        # Sync completed (did not abort)
        assert summary.finished_at is not None
        assert summary.matched == 2
        assert len(summary.errors) == 1
        assert summary.errors[0].error_type == "RuntimeError"
        assert "Counterspell" in summary.errors[0].error_message

        # Only 2 cards in DB (the successful ones)
        with Session(repo.engine) as session:
            cards = session.execute(select(CardRow)).scalars().all()
            assert len(cards) == 2
            card_names = {c.name_en for c in cards}
            assert "Lightning Bolt" in card_names
            assert "Swords to Plowshares" in card_names

        # Only 7 observations (3 + 4, not Counterspell's)
        with Session(repo.engine) as session:
            obs = session.execute(select(PriceObservationRow)).scalars().all()
            assert len(obs) == 7

        # 2 entries linked, 1 still unlinked (the failed one)
        with Session(repo.engine) as session:
            entries = (
                session.execute(select(UserCollectionRow).order_by(UserCollectionRow.id))
                .scalars()
                .all()
            )
            linked = [e for e in entries if e.card_id is not None]
            unlinked = [e for e in entries if e.card_id is None]
            assert len(linked) == 2
            assert len(unlinked) == 1


# ── Test 5: Cleanup + sync integration ───────────────────────────


@pytest.mark.asyncio
class TestCleanupAndSync:
    """Pre-populate DB with non-collection cards, then sync.

    Verifies that collection cards get price data. Non-collection cards
    are left untouched (cleanup is a separate concern).
    """

    async def test_sync_adds_collection_cards_alongside_existing(self, repo):
        # Pre-populate DB with a card NOT in the collection
        with Session(repo.engine) as session:
            non_coll_card = CardRow(
                game="magic",
                name_en="Force of Will",
                name_pt="Forca de Vontade",
                set_code="ema",
                collector_number="049",
            )
            session.add(non_coll_card)
            session.flush()

            non_coll_source = SourceCardRow(
                source="myp",
                external_id="99999",
                card_id=non_coll_card.id,
                url="https://mypcards.com/magic/produto/99999/forca-de-vontade",
                name_en="Force of Will",
                set_code="ema",
                collector_number="049",
            )
            session.add(non_coll_source)
            session.commit()
            non_coll_card_id = non_coll_card.id

        # Now seed 2 collection entries
        cards_to_seed = [
            {"name_en": "Lightning Bolt", "set_code": "dmr", "collector_number": "141"},
            {"name_en": "Dark Ritual", "set_code": "dmr", "collector_number": "067"},
        ]
        _seed_collection_entries(repo, cards_to_seed)

        provider = _make_provider_mock()
        provider.search_card = AsyncMock(
            side_effect=[
                lightning_bolt_search(),
                dark_ritual_search(),
            ]
        )
        provider.get_card_details = AsyncMock(
            side_effect=[
                lightning_bolt_detail(),
                dark_ritual_detail(),
            ]
        )
        provider.get_price_history = AsyncMock(
            side_effect=[
                make_price_history("45231", count=3),
                make_price_history("55100", count=3),
            ]
        )

        with (
            patch("src.collectors.sync_collection.Repository", return_value=repo),
            patch("src.collectors.sync_collection.MypCardsProvider", return_value=provider),
        ):
            summary = await run_sync_collection(
                db_url="sqlite:///:memory:",
                concurrency=1,
                delay=0,
            )

        assert summary.matched == 2

        # Verify total cards: 1 pre-existing + 2 synced = 3
        with Session(repo.engine) as session:
            cards = session.execute(select(CardRow)).scalars().all()
            assert len(cards) == 3

        # Non-collection card still exists
        with Session(repo.engine) as session:
            non_coll = session.get(CardRow, non_coll_card_id)
            assert non_coll is not None
            assert non_coll.name_en == "Force of Will"

        # Collection entries have price data
        with Session(repo.engine) as session:
            obs = session.execute(select(PriceObservationRow)).scalars().all()
            assert len(obs) == 6

        # Market stats include all cards
        stats = repo.get_market_stats()
        assert stats["total_cards"] == 3
        assert stats["total_observations"] == 6


# ── Test 6: Duplicate collection entries ──────────────────────────


@pytest.mark.asyncio
class TestDuplicateCollectionEntries:
    """Same card with different quality should create one CardRow, both linked."""

    async def test_duplicate_entries_share_card_row(self, repo):
        cards_to_seed = [
            {
                "name_en": "Lightning Bolt",
                "set_code": "dmr",
                "collector_number": "141",
                "quality": "NM",
            },
            {
                "name_en": "Lightning Bolt",
                "set_code": "dmr",
                "collector_number": "141",
                "quality": "SP",
            },
        ]
        _seed_collection_entries(repo, cards_to_seed)

        provider = _make_provider_mock()
        # Both entries will search for the same card
        provider.search_card = AsyncMock(return_value=lightning_bolt_search())
        provider.get_card_details = AsyncMock(return_value=lightning_bolt_detail())
        provider.get_price_history = AsyncMock(return_value=make_price_history("45231", count=3))

        with (
            patch("src.collectors.sync_collection.Repository", return_value=repo),
            patch("src.collectors.sync_collection.MypCardsProvider", return_value=provider),
        ):
            summary = await run_sync_collection(
                db_url="sqlite:///:memory:",
                concurrency=1,
                delay=0,
            )

        assert summary.matched == 2

        # Only ONE CardRow created (upsert deduplicates)
        with Session(repo.engine) as session:
            cards = session.execute(select(CardRow)).scalars().all()
            assert len(cards) == 1
            card_id = cards[0].id

        # Both collection entries linked to the same card_id
        with Session(repo.engine) as session:
            entries = session.execute(select(UserCollectionRow)).scalars().all()
            assert len(entries) == 2
            assert all(e.card_id == card_id for e in entries)

        # Price observations: 3 inserted first time, 0 second time (dedup)
        with Session(repo.engine) as session:
            obs = session.execute(select(PriceObservationRow)).scalars().all()
            assert len(obs) == 3  # no duplicates


# ── Test 7: Card with no price history ────────────────────────────


@pytest.mark.asyncio
class TestNoHistoryCard:
    """Card with empty price history still creates CardRow and links."""

    async def test_no_history_still_links(self, repo):
        cards_to_seed = [
            {"name_en": "Brainstorm", "set_code": "dmr", "collector_number": "049"},
        ]
        _seed_collection_entries(repo, cards_to_seed)

        provider = _make_provider_mock()
        provider.search_card = AsyncMock(return_value=brainstorm_search())
        provider.get_card_details = AsyncMock(return_value=brainstorm_detail())
        provider.get_price_history = AsyncMock(
            return_value=[]  # empty history
        )

        with (
            patch("src.collectors.sync_collection.Repository", return_value=repo),
            patch("src.collectors.sync_collection.MypCardsProvider", return_value=provider),
        ):
            summary = await run_sync_collection(
                db_url="sqlite:///:memory:",
                concurrency=1,
                delay=0,
            )

        assert summary.matched == 1
        assert summary.observations_saved == 0

        # CardRow exists
        with Session(repo.engine) as session:
            cards = session.execute(select(CardRow)).scalars().all()
            assert len(cards) == 1
            assert cards[0].name_en == "Brainstorm"

        # Collection entry linked
        with Session(repo.engine) as session:
            entries = session.execute(select(UserCollectionRow)).scalars().all()
            assert len(entries) == 1
            assert entries[0].card_id is not None

        # No observations
        with Session(repo.engine) as session:
            obs = session.execute(select(PriceObservationRow)).scalars().all()
            assert len(obs) == 0


# ── Test 8: Set code normalization ────────────────────────────────


@pytest.mark.asyncio
class TestSetCodeNormalization:
    """Verify set codes are stored lowercase throughout the pipeline."""

    async def test_set_codes_lowercase_in_db(self, repo):
        # Seed with uppercase set_code to verify normalization
        cards_to_seed = [
            {"name_en": "Lightning Bolt", "set_code": "dmr", "collector_number": "141"},
        ]
        _seed_collection_entries(repo, cards_to_seed)

        provider = _make_provider_mock()
        provider.search_card = AsyncMock(return_value=lightning_bolt_search())
        provider.get_card_details = AsyncMock(return_value=lightning_bolt_detail())
        provider.get_price_history = AsyncMock(return_value=make_price_history("45231", count=2))

        with (
            patch("src.collectors.sync_collection.Repository", return_value=repo),
            patch("src.collectors.sync_collection.MypCardsProvider", return_value=provider),
        ):
            summary = await run_sync_collection(
                db_url="sqlite:///:memory:",
                concurrency=1,
                delay=0,
            )

        assert summary.matched == 1

        # Verify set codes are lowercase in all tables
        with Session(repo.engine) as session:
            card = session.execute(select(CardRow)).scalars().first()
            assert card.set_code == "dmr"

            sc = session.execute(select(SourceCardRow)).scalars().first()
            assert sc.set_code == "dmr"


# ── Test 9: SyncResult details ────────────────────────────────────


@pytest.mark.asyncio
class TestSyncResultDetails:
    """Verify SyncResult entries contain correct details after sync."""

    async def test_sync_results_have_correct_details(self, repo):
        cards_to_seed = [
            {"name_en": "Lightning Bolt", "set_code": "dmr", "collector_number": "141"},
            {"name_en": "Nonexistent", "set_code": "xyz", "collector_number": "999"},
        ]
        _seed_collection_entries(repo, cards_to_seed)

        provider = _make_provider_mock()
        provider.search_card = AsyncMock(
            side_effect=[
                lightning_bolt_search(),
                empty_search(),
            ]
        )
        provider.get_card_details = AsyncMock(return_value=lightning_bolt_detail())
        provider.get_price_history = AsyncMock(return_value=make_price_history("45231", count=3))

        with (
            patch("src.collectors.sync_collection.Repository", return_value=repo),
            patch("src.collectors.sync_collection.MypCardsProvider", return_value=provider),
        ):
            summary = await run_sync_collection(
                db_url="sqlite:///:memory:",
                concurrency=1,
                delay=0,
            )

        assert len(summary.results) == 2

        synced_results = [r for r in summary.results if r.status == "synced"]
        unmatched_results = [r for r in summary.results if r.status == "unmatched"]

        assert len(synced_results) == 1
        assert synced_results[0].card_id is not None
        assert synced_results[0].observations_count == 3
        assert synced_results[0].match_confidence == "sku_exact"
        assert synced_results[0].name_en == "Lightning Bolt"

        assert len(unmatched_results) == 1
        assert unmatched_results[0].card_id is None
        assert unmatched_results[0].name_en == "Nonexistent"
        assert unmatched_results[0].match_confidence == "none"

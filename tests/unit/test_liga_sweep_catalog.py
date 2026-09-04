"""Tests for liga_sweep catalog mode (collection_only=False)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.collectors.liga_sweep import run_liga_sweep
from src.database.models import CardRow, PriceObservationRow, SourceCardRow
from src.database.repository import Repository

# ── Helpers ──────────────────────────────────────────────────────────


def _make_catalog_card(card_id: int, name_en: str = "Card", set_code: str = "DMU") -> dict:
    return {
        "card_id": card_id,
        "name_en": name_en,
        "name_pt": None,
        "set_code": set_code,
        "collector_number": str(card_id),
        "extras": None,
    }


def _seed_catalog_card(
    session,
    card_id: int,
    name_en: str = "Card",
    set_code: str = "DMU",
    collector_number: str = "1",
):
    """Insert a card + source_card into the DB for catalog scan testing."""
    card = CardRow(
        id=card_id,
        game="magic",
        name_en=name_en,
        set_code=set_code,
        collector_number=collector_number,
    )
    session.add(card)
    session.flush()
    source = SourceCardRow(
        source="liga",
        external_id=f"liga_catalog_{set_code}_{collector_number}",
        card_id=card_id,
        url=f"https://ligamagic.com.br/?view=card&id={card_id}",
        name_en=name_en,
        set_code=set_code,
        collector_number=collector_number,
    )
    session.add(source)
    session.flush()
    return card, source


def _seed_price_observation(session, card_id: int, observed_at: date):
    """Insert a liga price observation for the given card_id."""
    obs = PriceObservationRow(
        source="liga",
        external_id=f"liga_{card_id}",
        observed_at=observed_at,
        median_price=Decimal("5.00"),
        currency="BRL",
    )
    session.add(obs)
    session.flush()
    return obs


@pytest.fixture()
def repo(tmp_path):
    """Create a fresh in-memory repository with tables."""
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    return Repository(db_url)


# ── Repository: get_catalog_cards_for_liga_scan ──────────────────────


class TestGetCatalogCardsForLigaScan:
    def test_returns_catalog_cards(self, repo):
        """Cards with source='liga' in source_cards should be returned."""
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            _seed_catalog_card(session, 1, "Lightning Bolt", "DMU", "1")
            _seed_catalog_card(session, 2, "Counterspell", "DMU", "2")
            session.commit()

        result = repo.get_catalog_cards_for_liga_scan(max_age_days=7)

        assert len(result) == 2
        assert result[0]["card_id"] == 1
        assert result[0]["name_en"] == "Lightning Bolt"
        assert result[0]["extras"] is None
        assert result[1]["card_id"] == 2

    def test_only_magic_cards(self, repo):
        """Non-magic cards should be excluded."""
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            _seed_catalog_card(session, 1, "Lightning Bolt", "DMU", "1")
            # Add a non-magic card
            other_card = CardRow(
                id=99, game="pokemon", name_en="Pikachu", set_code="BASE", collector_number="1"
            )
            session.add(other_card)
            session.flush()
            other_source = SourceCardRow(
                source="liga",
                external_id="liga_catalog_BASE_1",
                card_id=99,
                url="https://example.com",
                name_en="Pikachu",
            )
            session.add(other_source)
            session.commit()

        result = repo.get_catalog_cards_for_liga_scan(max_age_days=7)

        assert len(result) == 1
        assert result[0]["name_en"] == "Lightning Bolt"

    def test_only_liga_source(self, repo):
        """Cards with source != 'liga' in source_cards should be excluded."""
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            _seed_catalog_card(session, 1, "Lightning Bolt", "DMU", "1")
            # Add a card with different source
            card2 = CardRow(
                id=2, game="magic", name_en="Counterspell", set_code="DMU", collector_number="2"
            )
            session.add(card2)
            session.flush()
            myp_source = SourceCardRow(
                source="myp",
                external_id="myp_123",
                card_id=2,
                url="https://mypcards.com/123",
                name_en="Counterspell",
            )
            session.add(myp_source)
            session.commit()

        result = repo.get_catalog_cards_for_liga_scan(max_age_days=7)

        assert len(result) == 1
        assert result[0]["name_en"] == "Lightning Bolt"

    def test_set_codes_filter(self, repo):
        """set_codes filter should restrict results."""
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            _seed_catalog_card(session, 1, "Lightning Bolt", "DMU", "1")
            _seed_catalog_card(session, 2, "Counterspell", "MH2", "1")
            _seed_catalog_card(session, 3, "Brainstorm", "DMU", "2")
            session.commit()

        result = repo.get_catalog_cards_for_liga_scan(set_codes=["DMU"], max_age_days=7)

        assert len(result) == 2
        names = {r["name_en"] for r in result}
        assert names == {"Lightning Bolt", "Brainstorm"}

    def test_set_codes_multiple(self, repo):
        """Multiple set_codes should all be included."""
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            _seed_catalog_card(session, 1, "Card A", "DMU", "1")
            _seed_catalog_card(session, 2, "Card B", "MH2", "1")
            _seed_catalog_card(session, 3, "Card C", "BRO", "1")
            session.commit()

        result = repo.get_catalog_cards_for_liga_scan(set_codes=["DMU", "MH2"], max_age_days=7)

        assert len(result) == 2
        names = {r["name_en"] for r in result}
        assert names == {"Card A", "Card B"}

    def test_max_age_days_excludes_recent(self, repo):
        """Cards with a recent liga price observation should be excluded."""
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            _seed_catalog_card(session, 1, "Lightning Bolt", "DMU", "1")
            _seed_catalog_card(session, 2, "Counterspell", "DMU", "2")
            # Card 1 has a recent price (today)
            _seed_price_observation(session, 1, date.today())
            session.commit()

        result = repo.get_catalog_cards_for_liga_scan(max_age_days=7)

        assert len(result) == 1
        assert result[0]["name_en"] == "Counterspell"

    def test_max_age_days_includes_old_prices(self, repo):
        """Cards with old price observations should be included."""
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            _seed_catalog_card(session, 1, "Lightning Bolt", "DMU", "1")
            # Card 1 has an old price (10 days ago)
            _seed_price_observation(session, 1, date.today() - timedelta(days=10))
            session.commit()

        result = repo.get_catalog_cards_for_liga_scan(max_age_days=7)

        assert len(result) == 1
        assert result[0]["name_en"] == "Lightning Bolt"

    def test_limit(self, repo):
        """limit should restrict the number of results."""
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            for i in range(1, 6):
                _seed_catalog_card(session, i, f"Card {i}", "DMU", str(i))
            session.commit()

        result = repo.get_catalog_cards_for_liga_scan(max_age_days=7, limit=3)

        assert len(result) == 3

    def test_no_set_codes_returns_all(self, repo):
        """When set_codes is None, all magic+liga cards should be returned."""
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            _seed_catalog_card(session, 1, "Card A", "DMU", "1")
            _seed_catalog_card(session, 2, "Card B", "MH2", "1")
            session.commit()

        result = repo.get_catalog_cards_for_liga_scan(set_codes=None, max_age_days=7)

        assert len(result) == 2

    def test_dict_format_compatible(self, repo):
        """Returned dicts must have the keys expected by _fetch_liga_price."""
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            _seed_catalog_card(session, 1, "Lightning Bolt", "DMU", "42")
            session.commit()

        result = repo.get_catalog_cards_for_liga_scan(max_age_days=7)

        assert len(result) == 1
        card = result[0]
        assert "card_id" in card
        assert "name_en" in card
        assert "name_pt" in card
        assert "set_code" in card
        assert "collector_number" in card
        assert "extras" in card
        assert card["extras"] is None
        assert card["set_code"] == "DMU"
        assert card["collector_number"] == "42"


# ── run_liga_sweep: collection_only=False ────────────────────────────


class TestRunLigaSweepCatalogMode:
    @pytest.mark.asyncio
    async def test_catalog_mode_calls_catalog_query(self):
        """collection_only=False should call get_catalog_cards_for_liga_scan."""
        mock_repo = MagicMock()
        mock_repo.get_catalog_cards_for_liga_scan.return_value = []

        with (
            patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
            patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        ):
            result = await run_liga_sweep(
                db_url="sqlite:///:memory:",
                collection_only=False,
                dry_run=True,
            )

        mock_repo.get_catalog_cards_for_liga_scan.assert_called_once()
        mock_repo.get_cards_for_liga_scan.assert_not_called()
        assert result.dry_run is True
        assert result.total_eligible == 0

    @pytest.mark.asyncio
    async def test_collection_mode_calls_collection_query(self):
        """collection_only=True (default) should call get_cards_for_liga_scan."""
        mock_repo = MagicMock()
        mock_repo.get_cards_for_liga_scan.return_value = []

        with (
            patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
            patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        ):
            await run_liga_sweep(
                db_url="sqlite:///:memory:",
                collection_only=True,
                dry_run=True,
            )

        mock_repo.get_cards_for_liga_scan.assert_called_once()
        mock_repo.get_catalog_cards_for_liga_scan.assert_not_called()

    @pytest.mark.asyncio
    async def test_default_is_collection_only(self):
        """Default behavior should be collection_only=True."""
        mock_repo = MagicMock()
        mock_repo.get_cards_for_liga_scan.return_value = []

        with (
            patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
            patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        ):
            await run_liga_sweep(db_url="sqlite:///:memory:", dry_run=True)

        mock_repo.get_cards_for_liga_scan.assert_called_once()
        mock_repo.get_catalog_cards_for_liga_scan.assert_not_called()

    @pytest.mark.asyncio
    async def test_catalog_mode_passes_set_filter(self):
        """set_filter should be passed as set_codes to catalog query."""
        mock_repo = MagicMock()
        mock_repo.get_catalog_cards_for_liga_scan.return_value = []

        with (
            patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
            patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        ):
            await run_liga_sweep(
                db_url="sqlite:///:memory:",
                collection_only=False,
                set_filter="DMU",
                dry_run=True,
            )

        call_kwargs = mock_repo.get_catalog_cards_for_liga_scan.call_args.kwargs
        assert call_kwargs["set_codes"] == ["DMU"]

    @pytest.mark.asyncio
    async def test_catalog_mode_passes_max_age_days(self):
        """max_age_days should be forwarded to catalog query."""
        mock_repo = MagicMock()
        mock_repo.get_catalog_cards_for_liga_scan.return_value = []

        with (
            patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
            patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        ):
            await run_liga_sweep(
                db_url="sqlite:///:memory:",
                collection_only=False,
                max_age_days=14,
                dry_run=True,
            )

        call_kwargs = mock_repo.get_catalog_cards_for_liga_scan.call_args.kwargs
        assert call_kwargs["max_age_days"] == 14

    @pytest.mark.asyncio
    async def test_catalog_mode_passes_limit(self):
        """limit should be forwarded to catalog query."""
        mock_repo = MagicMock()
        mock_repo.get_catalog_cards_for_liga_scan.return_value = []

        with (
            patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
            patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        ):
            await run_liga_sweep(
                db_url="sqlite:///:memory:",
                collection_only=False,
                limit=50,
                dry_run=True,
            )

        call_kwargs = mock_repo.get_catalog_cards_for_liga_scan.call_args.kwargs
        assert call_kwargs["limit"] == 50

    @pytest.mark.asyncio
    async def test_catalog_mode_sweep_with_prices(self):
        """Full sweep in catalog mode should fetch and save prices."""
        cards = [_make_catalog_card(1, "Card A"), _make_catalog_card(2, "Card B")]
        mock_repo = MagicMock()
        mock_repo.get_catalog_cards_for_liga_scan.return_value = cards
        mock_repo.insert_price_observations.return_value = 1

        mock_provider = AsyncMock()
        mock_provider.open = AsyncMock()
        mock_provider.close = AsyncMock()

        async def _search(name):
            return {"normal": {"low": Decimal("1.50"), "mid": None, "high": None}}

        mock_provider.search_card = AsyncMock(side_effect=_search)

        with (
            patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
            patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
            patch("src.providers.liga.provider.LigaMagicProvider", return_value=mock_provider),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await run_liga_sweep(
                db_url="sqlite:///:memory:",
                collection_only=False,
                delay=0,
            )

        assert result.total_eligible == 2
        assert result.total_processed == 2
        assert result.prices_found == 2
        assert result.prices_not_found == 0
        assert result.errors == 0
        assert mock_repo.insert_price_observations.call_count == 2

    @pytest.mark.asyncio
    async def test_catalog_mode_no_set_filter(self):
        """When set_filter is None, set_codes should be None."""
        mock_repo = MagicMock()
        mock_repo.get_catalog_cards_for_liga_scan.return_value = []

        with (
            patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
            patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        ):
            await run_liga_sweep(
                db_url="sqlite:///:memory:",
                collection_only=False,
                set_filter=None,
                dry_run=True,
            )

        call_kwargs = mock_repo.get_catalog_cards_for_liga_scan.call_args.kwargs
        assert call_kwargs["set_codes"] is None

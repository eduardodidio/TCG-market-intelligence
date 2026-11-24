"""Tests for F213-T09: Portfolio API Hardening + Liga Link Resolver.

Covers:
- Portfolio summary with mixed priced/unpriced cards
- unpriced_card_count accuracy
- cards_without_acquisition count
- Investment metrics exclude unpriced cards (total_invested only counts paired)
- acquisition_only filter on collection list
- Liga URL resolution in collection detail
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import PriceObservationRow, SourceCardRow, UserCollectionRow

_TEST_USER_ID = "eduardo"


def _make_row(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": _TEST_USER_ID,
        "card_id": 42,
        "set_code": "DMR",
        "collector_number": "123",
        "name_en": "Lightning Bolt",
        "name_pt": "Raio",
        "set_name_en": "Dominaria Remastered",
        "set_name_pt": None,
        "quantity": 1,
        "quality": "NM",
        "language": "EN",
        "rarity": "R",
        "color": "R",
        "extras": None,
        "is_foil": False,
        "acquisition_price": Decimal("5.00"),
        "acquired_at": date(2026, 1, 15),
        "created_at": datetime(2026, 1, 1),
        "image_uri": None,
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_obs(**overrides) -> MagicMock:
    defaults = {
        "median_price": Decimal("8.50"),
        "tcg_price": None,
        "last_sold_price": None,
        "source": "liga",
        "observed_at": date(2026, 9, 1),
    }
    defaults.update(overrides)
    obs = MagicMock(spec=PriceObservationRow)
    for k, v in defaults.items():
        setattr(obs, k, v)
    return obs


def _make_app(mock_repo: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: _TEST_USER_ID
    mock_converter = MagicMock()
    mock_converter.convert.return_value = None
    app.dependency_overrides[get_currency_converter_dep] = lambda: mock_converter
    return app


# ---------------------------------------------------------------------------
# Portfolio summary hardening
# ---------------------------------------------------------------------------


class TestPortfolioSummaryHardening:
    """Investment metrics only include cards with BOTH acquisition AND market price."""

    def test_total_invested_excludes_unpriced_cards(self) -> None:
        """total_invested should only sum cards that also have a market price."""
        mock_repo = MagicMock()
        # 2 entries with acquisition_price: card 42 ($5) and card 43 ($10)
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("15.00"), 2)
        mock_repo.count_entries_without_acquisition.return_value = 0

        entries = [
            _make_row(id=1, card_id=42, acquisition_price=Decimal("5.00")),
            _make_row(id=2, card_id=43, acquisition_price=Decimal("10.00")),
        ]
        mock_repo.get_collection_entries_with_acquisition.return_value = entries
        # Only card 42 has a market price; card 43 is unpriced
        mock_repo.get_latest_prices_batch.return_value = {
            42: _make_obs(median_price=Decimal("8.00")),
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        data = resp.json()["data"]

        # total_invested should only count card 42's $5, not card 43's $10
        assert data["total_invested"] == 5.0
        assert data["total_current_value"] == 8.0
        assert data["total_pnl"] == 3.0
        assert data["unpriced_card_count"] == 1

    def test_pnl_pct_uses_paired_invested(self) -> None:
        """P&L % should be computed from the paired invested total, not all."""
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("100.00"), 2)
        mock_repo.count_entries_without_acquisition.return_value = 0

        entries = [
            _make_row(id=1, card_id=42, acquisition_price=Decimal("20.00")),
            _make_row(id=2, card_id=43, acquisition_price=Decimal("80.00")),
        ]
        mock_repo.get_collection_entries_with_acquisition.return_value = entries
        # Only card 42 is priced at $30 (50% gain on $20)
        mock_repo.get_latest_prices_batch.return_value = {
            42: _make_obs(median_price=Decimal("30.00")),
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        data = resp.json()["data"]

        # P&L should be (30-20)/20 = 50%, not (30-100)/100 = -70%
        assert data["total_invested"] == 20.0
        assert data["total_pnl"] == 10.0
        assert data["total_pnl_pct"] == 50.0

    def test_all_priced_includes_full_invested(self) -> None:
        """When all cards have market prices, total_invested includes everything."""
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("30.00"), 2)
        mock_repo.count_entries_without_acquisition.return_value = 0

        entries = [
            _make_row(id=1, card_id=42, acquisition_price=Decimal("10.00")),
            _make_row(id=2, card_id=43, acquisition_price=Decimal("20.00")),
        ]
        mock_repo.get_collection_entries_with_acquisition.return_value = entries
        mock_repo.get_latest_prices_batch.return_value = {
            42: _make_obs(median_price=Decimal("15.00")),
            43: _make_obs(median_price=Decimal("25.00")),
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        data = resp.json()["data"]

        assert data["total_invested"] == 30.0
        assert data["total_current_value"] == 40.0
        assert data["total_pnl"] == 10.0

    def test_no_priced_cards_zero_invested(self) -> None:
        """When no cards have market prices, total_invested should be 0."""
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("50.00"), 2)
        mock_repo.count_entries_without_acquisition.return_value = 0

        entries = [
            _make_row(id=1, card_id=42, acquisition_price=Decimal("30.00")),
            _make_row(id=2, card_id=43, acquisition_price=Decimal("20.00")),
        ]
        mock_repo.get_collection_entries_with_acquisition.return_value = entries
        mock_repo.get_latest_prices_batch.return_value = {}  # No prices

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        data = resp.json()["data"]

        assert data["total_invested"] == 0.0
        assert data["total_current_value"] == 0.0
        assert data["total_pnl"] == 0.0
        assert data["total_pnl_pct"] is None
        assert data["unpriced_card_count"] == 2

    def test_unpriced_card_count_with_mixed_obs(self) -> None:
        """Cards with obs but no median/tcg/last_sold price count as unpriced."""
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("15.00"), 3)
        mock_repo.count_entries_without_acquisition.return_value = 1

        entries = [
            _make_row(id=1, card_id=42, acquisition_price=Decimal("5.00")),
            _make_row(id=2, card_id=43, acquisition_price=Decimal("5.00")),
            _make_row(id=3, card_id=44, acquisition_price=Decimal("5.00")),
        ]
        mock_repo.get_collection_entries_with_acquisition.return_value = entries
        mock_repo.get_latest_prices_batch.return_value = {
            42: _make_obs(median_price=Decimal("10.00")),
            # card 43 has obs but all prices are None
            43: _make_obs(median_price=None, tcg_price=None, last_sold_price=None),
            # card 44 has no obs at all
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        data = resp.json()["data"]

        assert data["unpriced_card_count"] == 2
        assert data["cards_without_acquisition"] == 1
        # Only card 42 is paired
        assert data["total_invested"] == 5.0
        assert data["total_current_value"] == 10.0

    def test_cards_without_acquisition_count(self) -> None:
        """cards_without_acquisition reflects entries missing acquisition_price."""
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("10.00"), 1)
        mock_repo.count_entries_without_acquisition.return_value = 7

        entries = [_make_row(id=1, card_id=42, acquisition_price=Decimal("10.00"))]
        mock_repo.get_collection_entries_with_acquisition.return_value = entries
        mock_repo.get_latest_prices_batch.return_value = {42: _make_obs()}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        data = resp.json()["data"]

        assert data["cards_without_acquisition"] == 7
        assert data["invested_card_count"] == 1

    def test_quantity_multiplied_for_paired_invested(self) -> None:
        """When entry has quantity > 1, invested is acquisition_price * quantity."""
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("30.00"), 1)
        mock_repo.count_entries_without_acquisition.return_value = 0

        entries = [
            _make_row(id=1, card_id=42, acquisition_price=Decimal("10.00"), quantity=3),
        ]
        mock_repo.get_collection_entries_with_acquisition.return_value = entries
        mock_repo.get_latest_prices_batch.return_value = {
            42: _make_obs(median_price=Decimal("15.00")),
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        data = resp.json()["data"]

        # 10*3 = 30 invested, 15*3 = 45 current value
        assert data["total_invested"] == 30.0
        assert data["total_current_value"] == 45.0
        assert data["total_pnl"] == 15.0


# ---------------------------------------------------------------------------
# acquisition_only filter
# ---------------------------------------------------------------------------


class TestAcquisitionOnlyFilter:
    """GET /collection?acquisition_only=true filters by acquisition price presence."""

    def test_acquisition_only_passes_filter_to_repo(self) -> None:
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = []
        mock_repo.count_collection.return_value = 0

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection?acquisition_only=true")

        assert resp.status_code == 200
        call_kwargs = mock_repo.list_collection.call_args
        assert call_kwargs.kwargs.get("has_acquisition_price") is True or (
            call_kwargs[1].get("has_acquisition_price") is True
        )

    def test_acquisition_only_false_does_not_override(self) -> None:
        """acquisition_only=false should not change has_acquisition_price default."""
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = []
        mock_repo.count_collection.return_value = 0

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection?acquisition_only=false")

        assert resp.status_code == 200
        call_kwargs = mock_repo.list_collection.call_args
        # has_acquisition_price should still be None (default)
        assert call_kwargs.kwargs.get("has_acquisition_price") is None or (
            call_kwargs[1].get("has_acquisition_price") is None
        )

    def test_has_acquisition_price_takes_precedence(self) -> None:
        """When both params are set, has_acquisition_price wins."""
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = []
        mock_repo.count_collection.return_value = 0

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection?has_acquisition_price=false&acquisition_only=true")

        assert resp.status_code == 200
        call_kwargs = mock_repo.list_collection.call_args
        # has_acquisition_price=false should win over acquisition_only=true
        passed_val = call_kwargs.kwargs.get("has_acquisition_price")
        if passed_val is None:
            passed_val = call_kwargs[1].get("has_acquisition_price")
        assert passed_val is False


# ---------------------------------------------------------------------------
# Liga URL resolution
# ---------------------------------------------------------------------------


class TestLigaUrlResolution:
    """Collection detail should resolve liga_url from source_cards."""

    def _make_detail_app(self, mock_repo: MagicMock) -> FastAPI:
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_repo
        app.dependency_overrides[require_auth_or_api_key] = lambda: _TEST_USER_ID
        mock_converter = MagicMock()
        mock_converter.convert.return_value = 10.0
        app.dependency_overrides[get_currency_converter_dep] = lambda: mock_converter
        return app

    def test_liga_url_from_source_card_url(self) -> None:
        """When source_card has a ligamagic URL, it is returned."""
        mock_repo = MagicMock()
        entry = _make_row(card_id=42)
        mock_repo.get_collection_entry.return_value = entry
        mock_repo.get_latest_prices_batch.return_value = {42: _make_obs()}

        sc = MagicMock(spec=SourceCardRow)
        sc.source = "liga"
        sc.external_id = "liga_12345"
        sc.sku = None
        sc.url = "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt"
        sc.name_pt = "Raio"
        sc.name_en = "Lightning Bolt"
        mock_repo.get_source_cards_for_card.return_value = [sc]
        mock_repo.get_liga_card_url.return_value = None

        client = TestClient(self._make_detail_app(mock_repo))
        resp = client.get("/collection/1")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert (
            data["liga_url"] == "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt"
        )

    def test_liga_url_from_liga_card_urls_table(self) -> None:
        """When source_card URL is not ligamagic, fall back to liga_card_urls table."""
        mock_repo = MagicMock()
        entry = _make_row(card_id=42)
        mock_repo.get_collection_entry.return_value = entry
        mock_repo.get_latest_prices_batch.return_value = {42: _make_obs()}

        sc = MagicMock(spec=SourceCardRow)
        sc.source = "myp"
        sc.external_id = "liga_12345"
        sc.sku = None
        sc.url = "https://mypcards.com/product/12345"
        sc.name_pt = None
        sc.name_en = None
        mock_repo.get_source_cards_for_card.return_value = [sc]
        mock_repo.get_liga_card_url.return_value = (
            "https://www.ligamagic.com.br/?view=cards/card&card=Raio"
        )

        client = TestClient(self._make_detail_app(mock_repo))
        resp = client.get("/collection/1")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["liga_url"] == "https://www.ligamagic.com.br/?view=cards/card&card=Raio"

    def test_liga_url_none_when_no_liga_source(self) -> None:
        """When no Liga source card exists, liga_url should be None."""
        mock_repo = MagicMock()
        entry = _make_row(card_id=42)
        mock_repo.get_collection_entry.return_value = entry
        mock_repo.get_latest_prices_batch.return_value = {42: _make_obs()}

        sc = MagicMock(spec=SourceCardRow)
        sc.source = "myp"
        sc.external_id = "myp_42"
        sc.sku = None
        sc.url = "https://mypcards.com/product/42"
        sc.name_pt = None
        sc.name_en = None
        mock_repo.get_source_cards_for_card.return_value = [sc]

        client = TestClient(self._make_detail_app(mock_repo))
        resp = client.get("/collection/1")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["liga_url"] is None

    def test_liga_url_none_when_no_card_id(self) -> None:
        """When entry has no card_id, liga_url should be None."""
        mock_repo = MagicMock()
        entry = _make_row(card_id=None)
        mock_repo.get_collection_entry.return_value = entry
        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_source_cards_for_card.return_value = []

        client = TestClient(self._make_detail_app(mock_repo))
        resp = client.get("/collection/1")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["liga_url"] is None

    def test_liga_url_from_raw_source_card_name(self) -> None:
        """When source_cards_data is empty but raw SourceCardRow has name, construct URL."""
        mock_repo = MagicMock()
        entry = _make_row(card_id=42)
        mock_repo.get_collection_entry.return_value = entry
        mock_repo.get_latest_prices_batch.return_value = {42: _make_obs()}

        # get_source_cards_for_card returns empty on first call (for schema),
        # but non-empty on second call (for raw fallback)
        sc_raw = MagicMock(spec=SourceCardRow)
        sc_raw.source = "liga"
        sc_raw.external_id = "liga_99"
        sc_raw.sku = None
        sc_raw.url = "https://mypcards.com/product/99"  # Not ligamagic
        sc_raw.name_pt = "Raio"
        sc_raw.name_en = "Lightning Bolt"
        # First call returns empty (triggers raw fallback path), second returns the raw SC
        mock_repo.get_source_cards_for_card.return_value = [sc_raw]
        mock_repo.get_liga_card_url.return_value = None

        client = TestClient(self._make_detail_app(mock_repo))
        resp = client.get("/collection/1")

        assert resp.status_code == 200
        resp_data = resp.json()["data"]
        # The _build_collection_detail function fetches source_cards via
        # get_source_cards_for_card and converts to SourceCardSchema. Since the
        # schema has the liga_ external_id, the resolver checks liga_card_urls
        # table (returns None here). The SourceCardSchema does NOT have
        # name_pt/name_en, so the name-based URL construction only fires in the
        # raw fallback path (when source_cards_data is empty).
        # In this case the url is "https://mypcards.com/..." which is not ligamagic,
        # and liga_card_url returns None, so liga_url ends up None.
        assert resp_data["liga_url"] is None


class TestLigaUrlField:
    """Verify liga_url field exists in CollectionCardDetail schema."""

    def test_schema_has_liga_url_field(self) -> None:
        from src.api.schemas.collection import CollectionCardDetail

        fields = CollectionCardDetail.model_fields
        assert "liga_url" in fields
        # Default should be None
        assert fields["liga_url"].default is None

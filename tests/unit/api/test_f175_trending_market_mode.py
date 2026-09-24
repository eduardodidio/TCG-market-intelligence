"""End-to-end regression tests for trending market vs collection mode (F175-T07).

Exercises GET /api/v1/market/trending/{gainers,losers} against a real SQLite
Repository (not a mocked repo), covering AC1-AC4 of F175.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.api.routers.market as market_module
from src.api.deps import get_currency_converter_dep, get_db
from src.auth.dependencies import get_optional_user
from src.database.models import CardRow, PriceObservationRow, SourceCardRow, UserCollectionRow
from src.database.repository import Repository
from src.domain.models import User
from src.services.currency import CurrencyConverter

RISING_CARD_ID = 101
FALLING_CARD_ID = 102
MYP_CARD_ID = 103


@pytest.fixture()
def repo(tmp_path) -> Repository:
    # A real file-backed SQLite DB (not ":memory:") so the connection the
    # TestClient's request thread opens sees the same tables/rows the test
    # seeded on the main thread -- ":memory:" is per-connection and would
    # look empty from the request thread.
    db_path = tmp_path / "f175_trending.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture(autouse=True)
def _reset_trending_service_singleton():
    market_module._trending_service = None
    yield
    market_module._trending_service = None


def _seed_card(session, card_id: int, name: str) -> None:
    session.add(
        CardRow(
            id=card_id,
            game="magic",
            name_en=name,
            name_pt=name,
            set_code="TST",
            collector_number=str(card_id).zfill(3),
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )
    )


def _seed_series(
    session, source: str, external_id: str, prices: list[Decimal], start_days_ago: int
) -> None:
    for i, price in enumerate(prices):
        session.add(
            PriceObservationRow(
                source=source,
                external_id=external_id,
                observed_at=date.today() - timedelta(days=start_days_ago - i),
                median_price=price,
            )
        )


def _seed_market_and_collection_cards(repo: Repository, user_id: int | None = None) -> None:
    """Seed a rising Liga-only card, a falling Liga-only card, and a MYP card.

    Optionally adds a UserCollectionRow linking `user_id` to only the rising
    card, so collection-mode tests can assert the falling/MYP cards are
    excluded.
    """
    from sqlalchemy.orm import Session

    with Session(repo.engine) as session:
        _seed_card(session, RISING_CARD_ID, "Rising Card")
        _seed_card(session, FALLING_CARD_ID, "Falling Card")
        _seed_card(session, MYP_CARD_ID, "MYP Card")

        # Rising card: Liga sweep only (no source_cards row), 5 consecutive
        # rising days ending today.
        _seed_series(
            session,
            "liga",
            f"liga_{RISING_CARD_ID}",
            [
                Decimal("10.00"),
                Decimal("12.00"),
                Decimal("14.00"),
                Decimal("16.00"),
                Decimal("18.00"),
            ],
            start_days_ago=4,
        )

        # Falling card: Liga sweep only, 5 consecutive falling days.
        _seed_series(
            session,
            "liga",
            f"liga_{FALLING_CARD_ID}",
            [
                Decimal("18.00"),
                Decimal("16.00"),
                Decimal("14.00"),
                Decimal("12.00"),
                Decimal("10.00"),
            ],
            start_days_ago=4,
        )

        # MYP card: via source_cards, rising over 5 days.
        session.add(
            SourceCardRow(
                source="myp",
                external_id="myp_103",
                card_id=MYP_CARD_ID,
                url="https://example.com/myp_103",
                created_at=datetime(2026, 1, 1),
                updated_at=datetime(2026, 1, 1),
            )
        )
        _seed_series(
            session,
            "myp",
            "myp_103",
            [Decimal("5.00"), Decimal("6.00"), Decimal("7.00"), Decimal("8.00"), Decimal("9.00")],
            start_days_ago=4,
        )

        # liga_catalog_* data with no source_cards row: must be ignored, not
        # break the response.
        session.add(
            PriceObservationRow(
                source="liga",
                external_id="liga_catalog_tst_999",
                observed_at=date.today(),
                median_price=Decimal("50.00"),
            )
        )

        if user_id is not None:
            session.add(
                UserCollectionRow(
                    user_id=str(user_id),
                    card_id=RISING_CARD_ID,
                    set_code="TST",
                    collector_number=str(RISING_CARD_ID).zfill(3),
                    name_en="Rising Card",
                )
            )

        session.commit()


def _make_app(repo: Repository, user: User | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(market_module.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_currency_converter_dep] = lambda: CurrencyConverter(repo)
    app.dependency_overrides[get_optional_user] = lambda: user
    return app


def _user(uid: int = 7) -> User:
    return User(id=uid, email="test@example.com")


class TestMarketMode:
    def test_market_gainers_includes_liga_only_card(self, repo: Repository) -> None:
        _seed_market_and_collection_cards(repo)
        client = TestClient(_make_app(repo))

        resp = client.get("/api/v1/market/trending/gainers")

        assert resp.status_code == 200
        cards = resp.json()["data"]["cards"]
        card_ids = {c["card_id"] for c in cards}
        assert RISING_CARD_ID in card_ids

    def test_market_gainers_includes_myp_card(self, repo: Repository) -> None:
        _seed_market_and_collection_cards(repo)
        client = TestClient(_make_app(repo))

        resp = client.get("/api/v1/market/trending/gainers")

        assert resp.status_code == 200
        card_ids = {c["card_id"] for c in resp.json()["data"]["cards"]}
        assert MYP_CARD_ID in card_ids

    def test_market_losers_includes_falling_liga_card(self, repo: Repository) -> None:
        _seed_market_and_collection_cards(repo)
        client = TestClient(_make_app(repo))

        resp = client.get("/api/v1/market/trending/losers")

        assert resp.status_code == 200
        card_ids = {c["card_id"] for c in resp.json()["data"]["cards"]}
        assert FALLING_CARD_ID in card_ids

    def test_market_mode_works_for_authenticated_user_without_flag(self, repo: Repository) -> None:
        _seed_market_and_collection_cards(repo, user_id=7)
        client = TestClient(_make_app(repo, user=_user(7)))

        resp = client.get("/api/v1/market/trending/gainers")

        assert resp.status_code == 200
        card_ids = {c["card_id"] for c in resp.json()["data"]["cards"]}
        # Market mode: owned AND not-owned cards both show up.
        assert RISING_CARD_ID in card_ids
        assert MYP_CARD_ID in card_ids

    def test_liga_catalog_only_data_does_not_break_response(self, repo: Repository) -> None:
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id="liga_catalog_tst_999",
                    observed_at=date.today(),
                    median_price=Decimal("50.00"),
                )
            )
            session.commit()
        client = TestClient(_make_app(repo))

        resp = client.get("/api/v1/market/trending/gainers")

        assert resp.status_code == 200
        assert resp.json()["data"]["cards"] == []


class TestCollectionMode:
    def test_collection_only_returns_only_owned_card(self, repo: Repository) -> None:
        _seed_market_and_collection_cards(repo, user_id=7)
        client = TestClient(_make_app(repo, user=_user(7)))

        resp = client.get("/api/v1/market/trending/gainers?collection_only=true")

        assert resp.status_code == 200
        card_ids = {c["card_id"] for c in resp.json()["data"]["cards"]}
        assert card_ids == {RISING_CARD_ID}

    def test_anonymous_with_collection_only_falls_back_to_market(self, repo: Repository) -> None:
        _seed_market_and_collection_cards(repo)
        client = TestClient(_make_app(repo, user=None))

        resp = client.get("/api/v1/market/trending/gainers?collection_only=true")

        assert resp.status_code == 200
        card_ids = {c["card_id"] for c in resp.json()["data"]["cards"]}
        # Anonymous user: collection_only is ignored, market mode used.
        assert RISING_CARD_ID in card_ids
        assert MYP_CARD_ID in card_ids


class TestBoundaries:
    def test_period_7d_excludes_points_8_days_old(self, repo: Repository) -> None:
        from sqlalchemy.orm import Session

        with Session(repo.engine) as session:
            _seed_card(session, RISING_CARD_ID, "Rising Card")
            # All points older than 7 days -- should be excluded entirely.
            _seed_series(
                session,
                "liga",
                f"liga_{RISING_CARD_ID}",
                [Decimal("10.00"), Decimal("12.00"), Decimal("14.00")],
                start_days_ago=10,
            )
            session.commit()
        client = TestClient(_make_app(repo))

        resp = client.get("/api/v1/market/trending/gainers?period=7d")

        assert resp.status_code == 200
        assert resp.json()["data"]["cards"] == []

    def test_limit_param_restricts_result_count(self, repo: Repository) -> None:
        _seed_market_and_collection_cards(repo)
        client = TestClient(_make_app(repo))

        resp = client.get("/api/v1/market/trending/gainers?limit=1")

        assert resp.status_code == 200
        assert len(resp.json()["data"]["cards"]) == 1


class TestErrors:
    def test_invalid_period_returns_422(self, repo: Repository) -> None:
        client = TestClient(_make_app(repo))

        resp = client.get("/api/v1/market/trending/gainers?period=999d")

        assert resp.status_code == 422

    def test_repo_exception_returns_empty_and_is_not_cached(self, repo: Repository) -> None:
        _seed_market_and_collection_cards(repo)
        client = TestClient(_make_app(repo))

        call_count = 0
        original = repo.get_trending_price_data

        def _flaky(period_days: int):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("simulated timeout")
            return original(period_days)

        with patch.object(repo, "get_trending_price_data", side_effect=_flaky):
            first = client.get("/api/v1/market/trending/gainers")
            assert first.status_code == 200
            assert first.json()["data"]["cards"] == []

            second = client.get("/api/v1/market/trending/gainers")
            assert second.status_code == 200
            card_ids = {c["card_id"] for c in second.json()["data"]["cards"]}
            assert RISING_CARD_ID in card_ids

        assert call_count == 2

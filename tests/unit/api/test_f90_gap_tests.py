"""F90 QA gap-filling tests.

Covers edge cases identified during QA validation:
- T03: User with 0 collection cards -> empty trending
- T04: Scheduler token cost when card_count == 0
- T05: Liga returns malformed data (missing keys)
- T06: Duplicate card names in evaluation list
- T06: Promote when batch_add returns 0 added
- T05→T06: search-web result wired to create evaluation
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.deps import get_credit_service, get_current_user, get_db
from src.api.routers.card_search import router as card_search_router
from src.api.routers.evaluations import router as eval_router
from src.api.schemas.trending import TrendingResponse
from src.credits.service import CreditService
from src.database.models import Base, EvaluationEntryRow
from src.database.repository import Repository
from src.domain.models import User
from src.providers.liga.provider import LigaMagicProvider
from src.providers.registry import ProviderRegistry
from src.services.trending import TrendingService

_TEST_USER = User(
    id=1,
    email="test@example.com",
    display_name="Test",
    is_active=True,
    is_admin=False,
)


def _create_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


def _make_repo() -> Repository:
    repo = Repository.__new__(Repository)
    repo.engine = _create_test_db()
    return repo


def _create_eval_app(repo: Repository, user: User = _TEST_USER) -> FastAPI:
    app = FastAPI()
    app.include_router(eval_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: user
    return app


# ── T03: Trending with empty collection ──


class TestTrendingEmptyCollection:
    """T03: When user has 0 collection cards, trending returns empty."""

    def test_user_scoped_with_no_collection_returns_empty(self) -> None:
        repo = MagicMock()
        repo.get_trending_price_data_for_user.return_value = {}
        repo.get_card_info_batch.return_value = {}

        service = TrendingService(repo)
        converter = MagicMock()
        converter.get_display_rate.return_value = None
        converter.convert.side_effect = lambda v, d, c: v

        result = service.get_trending("up", 30, 20, converter, "BRL", user_id=99)
        assert isinstance(result, TrendingResponse)
        assert result.cards == []
        assert result.direction == "up"
        assert result.cached is False

    def test_user_scoped_down_with_no_collection_returns_empty(self) -> None:
        repo = MagicMock()
        repo.get_trending_price_data_for_user.return_value = {}
        repo.get_card_info_batch.return_value = {}

        service = TrendingService(repo)
        converter = MagicMock()
        converter.get_display_rate.return_value = None
        converter.convert.side_effect = lambda v, d, c: v

        result = service.get_trending("down", 30, 20, converter, "BRL", user_id=99)
        assert result.cards == []
        assert result.direction == "down"


# ── T04: Scheduler token cost when card_count == 0 ──


class TestSchedulerTokenCostZeroCards:
    """T04: When user has 0 collection cards, tokens should NOT be deducted."""

    def test_zero_card_count_skips_token_check(self) -> None:
        """If card_count is 0, the scheduler should skip credit check/deduction."""
        import threading

        from src.scheduler.service import ScanScheduler

        svc = ScanScheduler.__new__(ScanScheduler)
        svc._lock = threading.Lock()

        mock_repo = MagicMock()
        mock_repo.get_scheduled_scan.return_value = {
            "id": 1,
            "scan_type": "collection",
            "user_id": 42,
            "last_run_id": None,
            "filters_json": "{}",
        }
        # User has 0 cards
        mock_repo.count_collection.return_value = 0
        mock_repo.create_scan_run.return_value = 100

        svc._db_url = "sqlite:///:memory:"

        with patch("src.scheduler.service.Repository", return_value=mock_repo):
            with patch("src.scheduler.service.CreditService") as mock_credit_cls:
                # The scan itself will fail but we just want to
                # verify the token path
                try:
                    svc._execute_scheduled_scan(1)
                except Exception:
                    pass
                # CreditService should NOT be instantiated for 0 cards
                mock_credit_cls.assert_not_called()


# ── T05: Liga returns malformed data ──


class TestSearchWebMalformedData:
    """T05: What if Liga returns malformed/incomplete data."""

    def _make_provider(self):
        provider = MagicMock(spec=LigaMagicProvider)
        provider.source_name = "liga"
        provider.search_card = AsyncMock()
        return provider

    def _make_credit_svc(self):
        return MagicMock(spec=CreditService)

    def _make_app(self, provider, credit_svc=None):
        app = FastAPI()
        app.include_router(card_search_router)
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_user] = lambda: _TEST_USER
        app.dependency_overrides[get_credit_service] = lambda: (
            credit_svc or self._make_credit_svc()
        )
        if provider:
            registry = ProviderRegistry([provider])
            app.state.provider_registry = registry
        return app

    def test_missing_normal_key_returns_empty(self) -> None:
        """Liga returns dict without 'normal' or 'foil' keys."""
        provider = self._make_provider()
        provider.search_card.return_value = {"card_name": "Test Card"}

        app = self._make_app(provider)
        client = TestClient(app)
        resp = client.get("/cards/search-web", params={"q": "Test"})
        assert resp.status_code == 200
        # Missing normal/foil keys -> .get returns {} -> no prices -> empty
        assert resp.json()["data"] == []

    def test_normal_with_all_none_values(self) -> None:
        """Liga returns normal prices but all None."""
        provider = self._make_provider()
        provider.search_card.return_value = {
            "card_name": "Test Card",
            "normal": {"low": None, "mid": None, "high": None},
            "foil": {"low": None, "mid": None, "high": None},
        }

        app = self._make_app(provider)
        client = TestClient(app)
        resp = client.get("/cards/search-web", params={"q": "Test"})
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_only_foil_price_returns_result(self) -> None:
        """Liga returns only foil price, no normal."""
        provider = self._make_provider()
        provider.search_card.return_value = {
            "card_name": "Test Card",
            "normal": {"low": None, "mid": None, "high": None},
            "foil": {"low": Decimal("50.00"), "mid": None, "high": None},
        }

        mock_repo = MagicMock()
        mock_repo.list_cards.return_value = []

        app = FastAPI()
        app.include_router(card_search_router)
        app.dependency_overrides[get_db] = lambda: mock_repo
        app.dependency_overrides[get_current_user] = lambda: _TEST_USER
        app.dependency_overrides[get_credit_service] = lambda: self._make_credit_svc()
        registry = ProviderRegistry([provider])
        app.state.provider_registry = registry

        client = TestClient(app)
        resp = client.get("/cards/search-web", params={"q": "Test"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["foil_price"] == 50.0
        assert data[0]["normal_price"] is None

    def test_timeout_returns_504(self) -> None:
        """Liga search times out."""
        import asyncio

        provider = self._make_provider()

        async def slow_search(q):
            await asyncio.sleep(100)

        provider.search_card = slow_search

        app = self._make_app(provider)
        client = TestClient(app)

        # Patch the timeout to be very short
        with patch("src.api.routers.card_search._SEARCH_TIMEOUT_SECONDS", 0.001):
            resp = client.get("/cards/search-web", params={"q": "Test"})
            assert resp.status_code == 504
            assert "timed out" in resp.json()["detail"].lower()


# ── T06: Duplicate card names in evaluation list ──


class TestEvaluationDuplicateCardNames:
    """T06: Same card can be added to evaluation list multiple times."""

    def test_duplicate_card_name_allowed(self) -> None:
        """No unique constraint on (user_id, card_name) -- duplicates are allowed."""
        repo = _make_repo()
        client = TestClient(_create_eval_app(repo))

        resp1 = client.post(
            "/api/v1/evaluations",
            json={"card_name": "Lightning Bolt", "price_at_add": 5.00},
        )
        assert resp1.status_code == 201

        resp2 = client.post(
            "/api/v1/evaluations",
            json={"card_name": "Lightning Bolt", "price_at_add": 6.00},
        )
        assert resp2.status_code == 201

        # Both entries exist
        resp3 = client.get("/api/v1/evaluations")
        assert len(resp3.json()["data"]) == 2

    def test_duplicate_card_name_different_sets(self) -> None:
        """Same card from different sets should coexist."""
        repo = _make_repo()
        client = TestClient(_create_eval_app(repo))

        resp1 = client.post(
            "/api/v1/evaluations",
            json={
                "card_name": "Lightning Bolt",
                "set_code": "m21",
                "collector_number": "152",
            },
        )
        assert resp1.status_code == 201

        resp2 = client.post(
            "/api/v1/evaluations",
            json={
                "card_name": "Lightning Bolt",
                "set_code": "lea",
                "collector_number": "161",
            },
        )
        assert resp2.status_code == 201


# ── T06: Promote edge case -- batch_add returns 0 ──


class TestPromoteFailsWhenBatchAddReturnsZero:
    """T06: What if batch_add_entries returns added=0."""

    def test_promote_returns_400_when_add_fails(self) -> None:
        """If batch_add_entries adds 0 cards, promote should return 400."""
        repo = _make_repo()

        with Session(repo.engine) as session:
            entry = EvaluationEntryRow(
                user_id=_TEST_USER.id,
                card_name="Some Card",
            )
            session.add(entry)
            session.commit()
            entry_id = entry.id

        client = TestClient(_create_eval_app(repo))

        # Mock batch_add_entries to return 0 added
        mock_result = MagicMock()
        mock_result.added = 0

        with patch(
            "src.collection.batch_add.batch_add_entries",
            return_value=mock_result,
        ):
            resp = client.post(f"/api/v1/evaluations/{entry_id}/promote")
            assert resp.status_code == 400
            assert "Failed" in resp.json()["detail"]

        # Verify the eval entry was NOT deleted (since add failed)
        with Session(repo.engine) as session:
            remaining = session.get(EvaluationEntryRow, entry_id)
            assert remaining is not None


# ── T05→T06 Integration: web search result maps to evaluation create body ──


class TestSearchWebToEvaluationIntegration:
    """Verify the data contract between T05 WebSearchResult and T06 EvalCreateRequest."""

    def test_web_search_result_has_fields_for_eval_create(self) -> None:
        """WebSearchResult fields map to EvalCreateRequest fields."""
        from src.api.schemas.card_search import WebSearchResult
        from src.api.schemas.evaluations import EvalCreateRequest

        # Simulate a web search result
        result = WebSearchResult(
            card_name="Lightning Bolt",
            liga_url="https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt",
            normal_price=5.50,
            foil_price=None,
            local_card_id=42,
        )

        # Create an eval body from the result (mimicking frontend logic)
        eval_body = EvalCreateRequest(
            card_name=result.card_name,
            liga_url=result.liga_url,
            price_at_add=result.normal_price,
            card_id=result.local_card_id,
        )

        assert eval_body.card_name == "Lightning Bolt"
        assert eval_body.liga_url is not None
        assert eval_body.price_at_add == 5.50
        assert eval_body.card_id == 42

    def test_web_search_result_without_local_card(self) -> None:
        """When no local card match, card_id is None."""
        from src.api.schemas.card_search import WebSearchResult
        from src.api.schemas.evaluations import EvalCreateRequest

        result = WebSearchResult(
            card_name="New Card",
            normal_price=10.0,
        )

        eval_body = EvalCreateRequest(
            card_name=result.card_name,
            price_at_add=result.normal_price,
            card_id=result.local_card_id,
        )

        assert eval_body.card_id is None
        assert eval_body.liga_url is None

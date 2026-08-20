from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db
from src.api.routers.collect import router

app = FastAPI()
app.include_router(router)


def _make_mock_repo(
    *,
    latest_date: date | None = None,
    total_cards: int = 0,
    stale_cards: int = 0,
    recent_errors: int = 0,
) -> MagicMock:
    mock = MagicMock()
    mock.get_latest_observation_date.return_value = latest_date
    mock.get_source_card_count.return_value = total_cards
    mock.get_stale_cards_count.return_value = stale_cards
    mock.get_recent_errors_count.return_value = recent_errors
    return mock


class TestHealthEndpointReturns200:
    def test_health_endpoint_returns_200(self) -> None:
        mock = _make_mock_repo(
            latest_date=date(2026, 8, 18),
            total_cards=10,
            stale_cards=0,
            recent_errors=0,
        )
        app.dependency_overrides[get_db] = lambda: mock
        client = TestClient(app)
        response = client.get("/collect/health")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert "errors" in body
        assert body["errors"] == []
        assert "request_id" in body["meta"]
        app.dependency_overrides.clear()


class TestHealthStatusHealthy:
    def test_health_status_healthy(self) -> None:
        mock = _make_mock_repo(
            latest_date=date(2026, 8, 18),
            total_cards=100,
            stale_cards=10,
            recent_errors=0,
        )
        app.dependency_overrides[get_db] = lambda: mock
        client = TestClient(app)
        response = client.get("/collect/health")
        body = response.json()
        data = body["data"]
        assert data["status"] == "healthy"
        assert data["last_collection_at"] == "2026-08-18"
        assert data["next_expected_at"] == "2026-08-19"
        assert data["total_cards"] == 100
        assert data["stale_cards_count"] == 10
        assert data["recent_errors_count"] == 0
        app.dependency_overrides.clear()


class TestHealthStatusStale:
    def test_health_status_stale_when_majority_stale(self) -> None:
        mock = _make_mock_repo(
            latest_date=date(2026, 8, 1),
            total_cards=100,
            stale_cards=60,
            recent_errors=0,
        )
        app.dependency_overrides[get_db] = lambda: mock
        client = TestClient(app)
        response = client.get("/collect/health")
        body = response.json()
        assert body["data"]["status"] == "stale"
        app.dependency_overrides.clear()

    def test_health_status_stale_at_boundary(self) -> None:
        """Exactly 50% stale should NOT be stale (> 50% required)."""
        mock = _make_mock_repo(
            latest_date=date(2026, 8, 10),
            total_cards=100,
            stale_cards=50,
            recent_errors=0,
        )
        app.dependency_overrides[get_db] = lambda: mock
        client = TestClient(app)
        response = client.get("/collect/health")
        body = response.json()
        assert body["data"]["status"] == "healthy"
        app.dependency_overrides.clear()


class TestHealthStatusError:
    def test_health_status_error(self) -> None:
        mock = _make_mock_repo(
            latest_date=date(2026, 8, 18),
            total_cards=100,
            stale_cards=5,
            recent_errors=3,
        )
        app.dependency_overrides[get_db] = lambda: mock
        client = TestClient(app)
        response = client.get("/collect/health")
        body = response.json()
        assert body["data"]["status"] == "error"
        assert body["data"]["recent_errors_count"] == 3
        app.dependency_overrides.clear()

    def test_error_takes_priority_over_stale(self) -> None:
        """Even if cards are stale, errors should take priority."""
        mock = _make_mock_repo(
            latest_date=date(2026, 8, 1),
            total_cards=100,
            stale_cards=80,
            recent_errors=5,
        )
        app.dependency_overrides[get_db] = lambda: mock
        client = TestClient(app)
        response = client.get("/collect/health")
        body = response.json()
        assert body["data"]["status"] == "error"
        app.dependency_overrides.clear()


class TestHealthNullWhenNoData:
    def test_health_null_when_no_data(self) -> None:
        mock = _make_mock_repo(
            latest_date=None,
            total_cards=0,
            stale_cards=0,
            recent_errors=0,
        )
        app.dependency_overrides[get_db] = lambda: mock
        client = TestClient(app)
        response = client.get("/collect/health")
        body = response.json()
        data = body["data"]
        assert data["last_collection_at"] is None
        assert data["next_expected_at"] is None
        assert data["total_cards"] == 0
        assert data["status"] == "stale"
        app.dependency_overrides.clear()

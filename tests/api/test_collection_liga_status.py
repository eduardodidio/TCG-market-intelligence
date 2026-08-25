"""Tests for GET /collection/liga-status and GET /collection/liga-missing endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.collection import router

_TEST_USER_ID = "eduardo"


def _make_app(mock_repo: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: _TEST_USER_ID
    return app


class TestLigaStatusEndpoint:
    """Tests for GET /collection/liga-status."""

    def test_liga_status_returns_correct_response(self):
        repo = MagicMock()
        repo.get_liga_coverage_stats.return_value = {
            "total_cards": 100,
            "liga_priced": 60,
            "liga_stale": 10,
            "liga_missing": 30,
            "unlinked": 5,
            "coverage_pct": 60.0,
            "last_liga_scan": "2026-08-25",
        }
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get("/collection/liga-status")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["total_cards"] == 100
        assert data["liga_priced"] == 60
        assert data["liga_stale"] == 10
        assert data["liga_missing"] == 30
        assert data["unlinked"] == 5
        assert data["coverage_pct"] == 60.0
        assert data["last_liga_scan"] == "2026-08-25"

    def test_liga_status_empty_collection(self):
        repo = MagicMock()
        repo.get_liga_coverage_stats.return_value = {
            "total_cards": 0,
            "liga_priced": 0,
            "liga_stale": 0,
            "liga_missing": 0,
            "unlinked": 0,
            "coverage_pct": 0.0,
            "last_liga_scan": None,
        }
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get("/collection/liga-status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_cards"] == 0
        assert data["coverage_pct"] == 0.0
        assert data["last_liga_scan"] is None

    def test_liga_status_custom_stale_days(self):
        repo = MagicMock()
        repo.get_liga_coverage_stats.return_value = {
            "total_cards": 50,
            "liga_priced": 40,
            "liga_stale": 5,
            "liga_missing": 5,
            "unlinked": 0,
            "coverage_pct": 80.0,
            "last_liga_scan": "2026-08-20",
        }
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get("/collection/liga-status?stale_days=14")
        assert resp.status_code == 200
        repo.get_liga_coverage_stats.assert_called_once_with(_TEST_USER_ID, stale_days=14)

    def test_liga_status_full_coverage(self):
        repo = MagicMock()
        repo.get_liga_coverage_stats.return_value = {
            "total_cards": 50,
            "liga_priced": 50,
            "liga_stale": 0,
            "liga_missing": 0,
            "unlinked": 0,
            "coverage_pct": 100.0,
            "last_liga_scan": "2026-08-25",
        }
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get("/collection/liga-status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["coverage_pct"] == 100.0
        assert data["liga_missing"] == 0


class TestLigaMissingEndpoint:
    """Tests for GET /collection/liga-missing."""

    def test_liga_missing_returns_cards(self):
        repo = MagicMock()
        repo.get_liga_missing_cards.return_value = (
            [
                {
                    "id": 1,
                    "card_id": 42,
                    "set_code": "DMR",
                    "collector_number": "123",
                    "name_en": "Lightning Bolt",
                    "name_pt": "Raio",
                    "set_name_en": "Dominaria Remastered",
                    "quantity": 2,
                    "quality": "NM",
                    "language": "EN",
                    "rarity": "R",
                    "color": "R",
                    "extras": None,
                },
            ],
            1,
        )
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get("/collection/liga-missing")
        assert resp.status_code == 200

        body = resp.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["name_en"] == "Lightning Bolt"
        assert body["meta"]["total"] == 1

    def test_liga_missing_pagination(self):
        repo = MagicMock()
        cards = [
            {
                "id": i,
                "card_id": i + 100,
                "set_code": "DMR",
                "collector_number": str(i),
                "name_en": f"Card {i}",
                "name_pt": None,
                "set_name_en": "Dominaria Remastered",
                "quantity": 1,
                "quality": None,
                "language": None,
                "rarity": None,
                "color": None,
                "extras": None,
            }
            for i in range(1, 4)
        ]
        repo.get_liga_missing_cards.return_value = (cards[:2], 5)
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get("/collection/liga-missing?limit=2&offset=0")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 5
        # offset should indicate next page available
        assert body["meta"]["offset"] == 2

    def test_liga_missing_empty(self):
        repo = MagicMock()
        repo.get_liga_missing_cards.return_value = ([], 0)
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get("/collection/liga-missing")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    def test_liga_missing_includes_image_url(self):
        repo = MagicMock()
        repo.get_liga_missing_cards.return_value = (
            [
                {
                    "id": 1,
                    "card_id": 42,
                    "set_code": "DMR",
                    "collector_number": "123",
                    "name_en": "Lightning Bolt",
                    "name_pt": None,
                    "set_name_en": None,
                    "quantity": 1,
                    "quality": None,
                    "language": None,
                    "rarity": None,
                    "color": None,
                    "extras": None,
                },
            ],
            1,
        )
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get("/collection/liga-missing")
        assert resp.status_code == 200
        card = resp.json()["data"][0]
        assert "scryfall.com" in card["image_url"]

    def test_liga_missing_last_page_no_next_offset(self):
        """When we're on the last page, offset in meta should be None."""
        repo = MagicMock()
        repo.get_liga_missing_cards.return_value = (
            [
                {
                    "id": 3,
                    "card_id": 103,
                    "set_code": "DMR",
                    "collector_number": "3",
                    "name_en": "Card 3",
                    "name_pt": None,
                    "set_name_en": None,
                    "quantity": 1,
                    "quality": None,
                    "language": None,
                    "rarity": None,
                    "color": None,
                    "extras": None,
                },
            ],
            3,
        )
        app = _make_app(repo)
        client = TestClient(app)

        resp = client.get("/collection/liga-missing?limit=2&offset=2")
        assert resp.status_code == 200
        body = resp.json()
        # offset=2 + limit=2 = 4 >= total=3, so no next page
        assert body["meta"]["offset"] is None

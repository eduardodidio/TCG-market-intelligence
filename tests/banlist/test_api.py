"""Tests for F41 banlist API router."""

from __future__ import annotations

import os
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.banlist import router


def _make_app(user_id: str = "user1") -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    mock_repo = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id

    app.state.mock_repo = mock_repo
    return app


class TestListBanlist:
    def test_returns_banned_cards(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_legalities_by_format.return_value = [
            {
                "card_id": 1,
                "format": "standard",
                "status": "banned",
                "effective_date": date(2026, 1, 1),
                "name_en": "Lightning Bolt",
                "name_pt": "Raio",
                "set_code": "lea",
                "collector_number": "161",
            },
        ]
        client = TestClient(app)
        resp = client.get("/banlist?format=standard&status=banned")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["status"] == "banned"
        assert data[0]["name_en"] == "Lightning Bolt"

    def test_default_shows_banned_and_restricted(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_legalities_by_format.side_effect = [
            [
                {
                    "card_id": 1,
                    "format": "standard",
                    "status": "banned",
                    "name_en": "Card A",
                    "name_pt": None,
                    "set_code": "lea",
                    "collector_number": "1",
                    "effective_date": None,
                }
            ],
            [
                {
                    "card_id": 2,
                    "format": "standard",
                    "status": "restricted",
                    "name_en": "Card B",
                    "name_pt": None,
                    "set_code": "lea",
                    "collector_number": "2",
                    "effective_date": None,
                }
            ],
        ]
        client = TestClient(app)
        resp = client.get("/banlist?format=standard")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2

    def test_no_results(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_legalities_by_format.return_value = []
        client = TestClient(app)
        resp = client.get("/banlist?format=standard&status=banned")
        assert resp.status_code == 200
        assert resp.json()["data"] == []


class TestListFormats:
    def test_returns_known_formats(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_known_formats.return_value = ["modern", "standard", "vintage"]
        client = TestClient(app)
        resp = client.get("/banlist/formats")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "standard" in data
        assert "modern" in data


class TestGetCardLegalities:
    def test_returns_legalities_for_card(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_legalities_for_card.return_value = [
            {"format": "standard", "status": "banned", "effective_date": None},
            {"format": "modern", "status": "legal", "effective_date": None},
        ]
        client = TestClient(app)
        resp = client.get("/banlist/card/42")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2
        formats = {d["format"] for d in data}
        assert formats == {"standard", "modern"}


class TestGetLegalityHistory:
    def test_returns_history(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_legality_history.return_value = [
            {
                "card_id": 1,
                "name_en": "Lightning Bolt",
                "format": "standard",
                "old_status": None,
                "new_status": "banned",
                "changed_at": datetime(2026, 8, 1),
            },
        ]
        client = TestClient(app)
        resp = client.get("/banlist/history")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["new_status"] == "banned"

    def test_filter_by_format(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_legality_history.return_value = []
        client = TestClient(app)
        resp = client.get("/banlist/history?format=standard")
        assert resp.status_code == 200
        mock_repo.get_legality_history.assert_called_once_with(
            card_id=None, format="standard", limit=50
        )


class TestSyncEndpoint:
    def test_requires_auth_without_override(self):
        """Without the auth override, sync should require auth."""
        app = FastAPI()
        app.include_router(router)
        mock_repo = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_repo
        # Do NOT override require_auth_or_api_key
        with patch.dict(os.environ, {"TCG_API_KEY": "test-key"}):
            client = TestClient(app)
            resp = client.post("/banlist/sync", json={"bulk": True})
        assert resp.status_code == 401

    def test_sync_with_auth_starts_job(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/banlist/sync", json={"bulk": True})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "running"
        assert "job_id" in data

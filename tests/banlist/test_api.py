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
    def test_returns_paginated_history(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_legality_history_paginated.return_value = (
            [
                {
                    "id": 1,
                    "card_id": 1,
                    "name_en": "Lightning Bolt",
                    "name_pt": "Raio",
                    "set_code": "lea",
                    "collector_number": "161",
                    "format": "standard",
                    "old_status": None,
                    "new_status": "banned",
                    "changed_at": datetime(2026, 8, 1),
                    "source": "scryfall_sync",
                },
            ],
            1,
        )
        client = TestClient(app)
        resp = client.get("/banlist/history")
        assert resp.status_code == 200
        wrapper = resp.json()["data"]
        assert wrapper["total"] == 1
        assert wrapper["limit"] == 50
        assert wrapper["offset"] == 0
        assert len(wrapper["items"]) == 1
        assert wrapper["items"][0]["new_status"] == "banned"
        assert wrapper["items"][0]["image_url"] is not None

    def test_filter_by_format(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_legality_history_paginated.return_value = ([], 0)
        client = TestClient(app)
        resp = client.get("/banlist/history?format=standard")
        assert resp.status_code == 200
        mock_repo.get_legality_history_paginated.assert_called_once_with(
            card_id=None,
            format="standard",
            date_from=None,
            date_to=None,
            limit=50,
            offset=0,
        )

    def test_date_range_filters(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_legality_history_paginated.return_value = ([], 0)
        client = TestClient(app)
        resp = client.get("/banlist/history?date_from=2026-01-01&date_to=2026-06-30")
        assert resp.status_code == 200
        call_kwargs = mock_repo.get_legality_history_paginated.call_args[1]
        assert call_kwargs["date_from"] == date(2026, 1, 1)
        assert call_kwargs["date_to"] == date(2026, 6, 30)

    def test_offset_pagination(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_legality_history_paginated.return_value = ([], 0)
        client = TestClient(app)
        resp = client.get("/banlist/history?offset=10&limit=5")
        assert resp.status_code == 200
        wrapper = resp.json()["data"]
        assert wrapper["offset"] == 10
        assert wrapper["limit"] == 5


class TestGetCardBanHistory:
    def test_returns_card_history(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_card_by_id.return_value = MagicMock()
        mock_repo.get_card_ban_history.return_value = [
            {
                "id": 10,
                "format": "standard",
                "old_status": "legal",
                "new_status": "banned",
                "changed_at": datetime(2026, 8, 1),
                "source": "scryfall_sync",
            },
            {
                "id": 11,
                "format": "modern",
                "old_status": None,
                "new_status": "legal",
                "changed_at": datetime(2026, 7, 1),
                "source": "scryfall_sync",
            },
        ]
        client = TestClient(app)
        resp = client.get("/banlist/card/42/history")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2
        assert data[0]["format"] == "standard"
        assert data[0]["source"] == "scryfall_sync"

    def test_card_not_found(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_card_by_id.return_value = None
        client = TestClient(app)
        resp = client.get("/banlist/card/9999/history")
        assert resp.status_code == 404


class TestGetBanImpact:
    def test_returns_stub_impact(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_card_by_id.return_value = MagicMock()
        mock_repo.get_ban_events_for_impact.return_value = [
            {
                "id": 1,
                "format": "standard",
                "old_status": "legal",
                "new_status": "banned",
                "changed_at": datetime(2026, 8, 1),
                "source": "scryfall_sync",
            },
        ]
        client = TestClient(app)
        resp = client.get("/banlist/impact/42")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["data_available"] is False
        assert data[0]["price_before"] is None
        assert data[0]["window_days"] == 7

    def test_respects_window_days(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_card_by_id.return_value = MagicMock()
        mock_repo.get_ban_events_for_impact.return_value = [
            {
                "id": 1,
                "format": "modern",
                "old_status": "legal",
                "new_status": "banned",
                "changed_at": datetime(2026, 8, 1),
                "source": "scryfall_sync",
            },
        ]
        client = TestClient(app)
        resp = client.get("/banlist/impact/42?window_days=14")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data[0]["window_days"] == 14

    def test_card_not_found(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_card_by_id.return_value = None
        client = TestClient(app)
        resp = client.get("/banlist/impact/9999")
        assert resp.status_code == 404


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

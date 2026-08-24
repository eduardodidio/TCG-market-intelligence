"""Tests for GET /api/v1/collection sort and offset query params."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db
from src.api.routers.collection import router
from src.database.models import UserCollectionRow


def _make_row(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": "eduardo",
        "card_id": None,
        "set_code": "DMR",
        "collector_number": "123",
        "name_en": "Lightning Bolt",
        "name_pt": "Raio",
        "set_name_en": "Dominaria Remastered",
        "quantity": 1,
        "quality": "NM",
        "language": "EN",
        "rarity": "R",
        "color": "R",
        "extras": None,
        "created_at": datetime(2026, 1, 1),
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_app(mock_repo: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: mock_repo
    return app


class TestSortQueryParams:
    def test_sort_by_name_asc_default(self):
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [_make_row()]
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/collection")
        assert resp.status_code == 200

        # Verify sort params passed to repo
        call_kwargs = mock_repo.list_collection.call_args.kwargs
        assert call_kwargs["sort_by"] == "name"
        assert call_kwargs["sort_dir"] == "asc"

    def test_sort_by_set_desc(self):
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [_make_row()]
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/collection?sort_by=set&sort_dir=desc")
        assert resp.status_code == 200

        call_kwargs = mock_repo.list_collection.call_args.kwargs
        assert call_kwargs["sort_by"] == "set"
        assert call_kwargs["sort_dir"] == "desc"

    def test_sort_by_number(self):
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [_make_row()]
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/collection?sort_by=number")
        assert resp.status_code == 200

        call_kwargs = mock_repo.list_collection.call_args.kwargs
        assert call_kwargs["sort_by"] == "number"

    def test_sort_by_added(self):
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [_make_row()]
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/collection?sort_by=added")
        assert resp.status_code == 200

        call_kwargs = mock_repo.list_collection.call_args.kwargs
        assert call_kwargs["sort_by"] == "added"

    def test_invalid_sort_by_returns_422(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/collection?sort_by=price")
        assert resp.status_code == 422

    def test_invalid_sort_dir_returns_422(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/collection?sort_dir=random")
        assert resp.status_code == 422


class TestOffsetPagination:
    def test_offset_passed_to_repo(self):
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [_make_row()]
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/collection?offset=10")
        assert resp.status_code == 200

        call_kwargs = mock_repo.list_collection.call_args.kwargs
        assert call_kwargs["offset"] == 10

    def test_offset_none_by_default(self):
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [_make_row()]
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/collection")
        assert resp.status_code == 200

        call_kwargs = mock_repo.list_collection.call_args.kwargs
        assert call_kwargs["offset"] == 0  # None becomes 0

    def test_negative_offset_returns_422(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/collection?offset=-1")
        assert resp.status_code == 422

    def test_next_offset_in_meta_when_has_next(self):
        mock_repo = MagicMock()
        # Return limit+1 rows to signal has_next
        rows = [_make_row(id=i) for i in range(1, 4)]
        mock_repo.list_collection.return_value = rows  # 3 rows for limit=2
        mock_repo.count_collection.return_value = 10
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/collection?offset=0&limit=2")
        assert resp.status_code == 200
        meta = resp.json()["meta"]
        assert meta["offset"] == 2  # next_offset = 0 + 2

    def test_no_next_offset_when_no_more_pages(self):
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [_make_row()]  # 1 row, limit=50
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/collection?offset=0")
        assert resp.status_code == 200
        meta = resp.json()["meta"]
        assert meta["offset"] is None

    def test_no_offset_in_meta_when_not_using_offset(self):
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [_make_row()]
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/collection")
        assert resp.status_code == 200
        meta = resp.json()["meta"]
        assert meta["offset"] is None


class TestBackwardCompat:
    def test_cursor_still_works(self):
        import base64

        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [_make_row()]
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        cursor = base64.urlsafe_b64encode(b"5").decode()
        client = TestClient(_make_app(mock_repo))
        resp = client.get(f"/api/v1/collection?cursor={cursor}")
        assert resp.status_code == 200

        call_kwargs = mock_repo.list_collection.call_args.kwargs
        assert call_kwargs["after_id"] == 5

    def test_name_and_set_filters_still_work(self):
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [_make_row()]
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/collection?name=bolt&set=DMR")
        assert resp.status_code == 200

        call_kwargs = mock_repo.list_collection.call_args.kwargs
        assert call_kwargs["name_search"] == "bolt"
        assert call_kwargs["set_code"] == "DMR"

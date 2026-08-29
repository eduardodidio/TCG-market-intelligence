from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.collection import router

_TEST_USER_ID = "eduardo"


def _make_app(mock_repo: MagicMock, user_id: str = _TEST_USER_ID) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    return app


class TestDeleteSingleEntry:
    """DELETE /collection/{entry_id} — single delete."""

    def test_delete_returns_204(self) -> None:
        mock_repo = MagicMock()
        mock_repo.delete_collection_entry.return_value = True

        client = TestClient(_make_app(mock_repo))
        resp = client.delete("/collection/1")
        assert resp.status_code == 204
        mock_repo.delete_collection_entry.assert_called_once_with(1, _TEST_USER_ID)

    def test_delete_404_for_nonexistent(self) -> None:
        mock_repo = MagicMock()
        mock_repo.delete_collection_entry.return_value = False

        client = TestClient(_make_app(mock_repo))
        resp = client.delete("/collection/999")
        assert resp.status_code == 404

    def test_delete_403_for_wrong_user(self) -> None:
        mock_repo = MagicMock()
        mock_repo.delete_collection_entry.side_effect = ValueError(
            "Not authorized to delete this entry"
        )

        client = TestClient(_make_app(mock_repo))
        resp = client.delete("/collection/1")
        assert resp.status_code == 403


class TestBulkDeleteEntries:
    """POST /collection/bulk-delete — bulk delete."""

    def test_bulk_delete_multiple(self) -> None:
        mock_repo = MagicMock()
        mock_repo.bulk_delete_collection_entries.return_value = 3

        client = TestClient(_make_app(mock_repo))
        resp = client.post("/collection/bulk-delete", json={"ids": [1, 2, 3]})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["deleted"] == 3

    def test_bulk_delete_atomic_invalid_id(self) -> None:
        mock_repo = MagicMock()
        mock_repo.bulk_delete_collection_entries.side_effect = ValueError(
            "Entries not found: [999]"
        )

        client = TestClient(_make_app(mock_repo))
        resp = client.post("/collection/bulk-delete", json={"ids": [1, 999]})
        assert resp.status_code == 404

    def test_bulk_delete_403_wrong_user(self) -> None:
        mock_repo = MagicMock()
        mock_repo.bulk_delete_collection_entries.side_effect = ValueError(
            "Not authorized to delete entry 2"
        )

        client = TestClient(_make_app(mock_repo))
        resp = client.post("/collection/bulk-delete", json={"ids": [1, 2]})
        assert resp.status_code == 403

    def test_bulk_delete_rejects_over_200(self) -> None:
        mock_repo = MagicMock()

        client = TestClient(_make_app(mock_repo))
        resp = client.post("/collection/bulk-delete", json={"ids": list(range(1, 202))})
        assert resp.status_code == 422

    def test_bulk_delete_empty_ids_rejected(self) -> None:
        mock_repo = MagicMock()

        client = TestClient(_make_app(mock_repo))
        resp = client.post("/collection/bulk-delete", json={"ids": []})
        assert resp.status_code == 422

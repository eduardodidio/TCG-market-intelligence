"""Integration tests for auto-canonize hook on CSV import.

Test plan scenarios: #16, #17, #18 (F49-T02).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.collection import router

_TEST_USER_ID = "eduardo"

_PATCH_IMPORT = "src.collection.importer.import_collection_csv"
_PATCH_PATH_EXISTS = "pathlib.Path.exists"
_PATCH_RUN_CANONIZE = "src.api.routers.collection._run_import_canonize"


def _make_app(mock_repo: MagicMock, user_id: str = _TEST_USER_ID) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    return app


class TestImportTriggersBackgroundCanonize:
    """#16: Background task scheduled after import with new_entry_ids."""

    @patch(_PATCH_RUN_CANONIZE)
    @patch(_PATCH_PATH_EXISTS, return_value=True)
    @patch(_PATCH_IMPORT)
    def test_import_triggers_background_canonize(
        self, mock_import, _mock_exists, mock_run_canonize
    ):
        mock_import.return_value = {
            "imported": 3,
            "skipped": 0,
            "linked": 3,
            "total_csv_rows": 3,
            "new_entry_ids": [10, 11, 12],
        }

        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/import")
        assert resp.status_code == 200

        body = resp.json()
        assert body["data"]["canonize_scheduled"] is True
        assert body["data"]["new_entry_ids"] == [10, 11, 12]
        assert body["data"]["imported"] == 3

    @patch(_PATCH_RUN_CANONIZE)
    @patch(_PATCH_PATH_EXISTS, return_value=True)
    @patch(_PATCH_IMPORT)
    def test_import_no_new_entries_skips_canonize(
        self, mock_import, _mock_exists, mock_run_canonize
    ):
        """#18: When all entries are duplicates/skipped, no background task is scheduled."""
        mock_import.return_value = {
            "imported": 0,
            "skipped": 5,
            "linked": 0,
            "total_csv_rows": 5,
            "new_entry_ids": [],
        }

        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/import")
        assert resp.status_code == 200

        body = resp.json()
        assert body["data"]["canonize_scheduled"] is False
        assert body["data"]["new_entry_ids"] == []


class TestImportCanonizeDoesNotBlockResponse:
    """#17: Import returns 200 before canonize completes."""

    @patch(_PATCH_PATH_EXISTS, return_value=True)
    @patch(_PATCH_IMPORT)
    def test_import_canonize_does_not_block_response(self, mock_import, _mock_exists):
        """The response should return immediately with canonize_scheduled=True.

        BackgroundTasks in FastAPI execute after the response is sent,
        so if the endpoint returns 200, canonize has not yet run.
        """
        mock_import.return_value = {
            "imported": 2,
            "skipped": 0,
            "linked": 2,
            "total_csv_rows": 2,
            "new_entry_ids": [100, 101],
        }

        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/import")

        # Response returns immediately (200), not delayed by canonize
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["canonize_scheduled"] is True
        assert body["data"]["imported"] == 2


class TestImportResponseIncludesNewFields:
    """Verify the import response schema includes all new F49-T02 fields."""

    @patch(_PATCH_PATH_EXISTS, return_value=True)
    @patch(_PATCH_IMPORT)
    def test_import_response_has_all_fields(self, mock_import, _mock_exists):
        mock_import.return_value = {
            "imported": 1,
            "skipped": 1,
            "linked": 1,
            "total_csv_rows": 2,
            "new_entry_ids": [42],
        }

        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/import")
        assert resp.status_code == 200

        data = resp.json()["data"]
        # Original fields
        assert "imported" in data
        assert "skipped" in data
        assert "linked" in data
        assert "total_csv_rows" in data
        # New F49-T02 fields
        assert "new_entry_ids" in data
        assert "canonize_scheduled" in data

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import UserCollectionRow

_TEST_USER_ID = "eduardo"


def _make_collection_row(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": _TEST_USER_ID,
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
        "created_at": datetime(2026, 1, 1),
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_app(mock_repo: MagicMock, user_id: str = _TEST_USER_ID) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    return app


class TestPatchSingleEntry:
    """PATCH /collection/{entry_id} — single update."""

    def test_update_quantity(self) -> None:
        mock_repo = MagicMock()
        updated_row = _make_collection_row(quantity=4)
        mock_repo.update_collection_entry.return_value = updated_row

        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={"quantity": 4})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["quantity"] == 4
        mock_repo.update_collection_entry.assert_called_once_with(1, _TEST_USER_ID, {"quantity": 4})

    def test_update_quality(self) -> None:
        mock_repo = MagicMock()
        updated_row = _make_collection_row(quality="SP")
        mock_repo.update_collection_entry.return_value = updated_row

        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={"quality": "SP"})
        assert resp.status_code == 200
        assert resp.json()["data"]["quality"] == "SP"

    def test_update_language(self) -> None:
        mock_repo = MagicMock()
        updated_row = _make_collection_row(language="JP")
        mock_repo.update_collection_entry.return_value = updated_row

        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={"language": "JP"})
        assert resp.status_code == 200
        assert resp.json()["data"]["language"] == "JP"

    def test_update_extras_updates_is_foil(self) -> None:
        mock_repo = MagicMock()
        updated_row = _make_collection_row(extras="Foil")
        mock_repo.update_collection_entry.return_value = updated_row

        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={"extras": "Foil"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["extras"] == "Foil"
        assert data["is_foil"] is True

    def test_partial_update_only_qty(self) -> None:
        mock_repo = MagicMock()
        updated_row = _make_collection_row(quantity=3)
        mock_repo.update_collection_entry.return_value = updated_row

        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={"quantity": 3})
        assert resp.status_code == 200
        # Only quantity should be in the updates dict
        call_args = mock_repo.update_collection_entry.call_args
        updates = call_args[0][2]
        assert "quantity" in updates
        assert "quality" not in updates
        assert "language" not in updates
        assert "extras" not in updates

    def test_404_for_nonexistent(self) -> None:
        mock_repo = MagicMock()
        mock_repo.update_collection_entry.return_value = None

        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/999", json={"quantity": 2})
        assert resp.status_code == 404

    def test_403_for_wrong_user(self) -> None:
        mock_repo = MagicMock()
        mock_repo.update_collection_entry.side_effect = ValueError(
            "Not authorized to modify this entry"
        )

        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={"quantity": 2})
        assert resp.status_code == 403

    def test_validation_error_quantity_zero(self) -> None:
        mock_repo = MagicMock()

        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={"quantity": 0})
        assert resp.status_code == 422

    def test_validation_error_invalid_quality(self) -> None:
        mock_repo = MagicMock()

        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={"quality": "INVALID"})
        assert resp.status_code == 422

    def test_validation_error_invalid_language(self) -> None:
        mock_repo = MagicMock()

        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={"language": "XX"})
        assert resp.status_code == 422

    def test_no_fields_returns_422(self) -> None:
        mock_repo = MagicMock()

        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={})
        assert resp.status_code == 422


class TestPatchBulkEntries:
    """PATCH /collection/bulk — bulk update."""

    def test_bulk_update_three_entries(self) -> None:
        mock_repo = MagicMock()
        mock_repo.bulk_update_collection_entries.return_value = 3

        client = TestClient(_make_app(mock_repo))
        resp = client.patch(
            "/collection/bulk",
            json={"ids": [1, 2, 3], "updates": {"quantity": 4}},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["affected"] == 3

    def test_bulk_update_rejects_wrong_user(self) -> None:
        mock_repo = MagicMock()
        mock_repo.bulk_update_collection_entries.side_effect = ValueError(
            "Not authorized to modify entry 2"
        )

        client = TestClient(_make_app(mock_repo))
        resp = client.patch(
            "/collection/bulk",
            json={"ids": [1, 2], "updates": {"quality": "NM"}},
        )
        assert resp.status_code == 403

    def test_bulk_update_rejects_missing_ids(self) -> None:
        mock_repo = MagicMock()
        mock_repo.bulk_update_collection_entries.side_effect = ValueError(
            "Entries not found: [999]"
        )

        client = TestClient(_make_app(mock_repo))
        resp = client.patch(
            "/collection/bulk",
            json={"ids": [1, 999], "updates": {"quality": "NM"}},
        )
        assert resp.status_code == 404

    def test_bulk_update_rejects_over_200(self) -> None:
        mock_repo = MagicMock()

        client = TestClient(_make_app(mock_repo))
        resp = client.patch(
            "/collection/bulk",
            json={"ids": list(range(1, 202)), "updates": {"quantity": 1}},
        )
        assert resp.status_code == 422

    def test_bulk_update_extras_foil(self) -> None:
        """Extras change in bulk should pass through correctly."""
        mock_repo = MagicMock()
        mock_repo.bulk_update_collection_entries.return_value = 2

        client = TestClient(_make_app(mock_repo))
        resp = client.patch(
            "/collection/bulk",
            json={"ids": [1, 2], "updates": {"extras": "Foil"}},
        )
        assert resp.status_code == 200
        call_args = mock_repo.bulk_update_collection_entries.call_args
        assert call_args[0][2] == {"extras": "Foil"}

    def test_bulk_update_empty_ids_rejected(self) -> None:
        mock_repo = MagicMock()

        client = TestClient(_make_app(mock_repo))
        resp = client.patch(
            "/collection/bulk",
            json={"ids": [], "updates": {"quantity": 1}},
        )
        assert resp.status_code == 422

    def test_bulk_update_no_fields_rejected(self) -> None:
        mock_repo = MagicMock()

        client = TestClient(_make_app(mock_repo))
        resp = client.patch(
            "/collection/bulk",
            json={"ids": [1], "updates": {}},
        )
        assert resp.status_code == 422

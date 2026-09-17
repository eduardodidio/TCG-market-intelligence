"""Tests for src.api.routers.purchases (import-preview + apply)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_current_user, get_db
from src.api.routers.purchases import router
from src.database.models import UserCollectionRow

_TEST_USER_ID = 1


def _fake_user():
    user = MagicMock()
    user.id = _TEST_USER_ID
    return user


def _make_entry(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": str(_TEST_USER_ID),
        "card_id": 42,
        "set_code": "afr",
        "collector_number": "139",
        "name_en": "Dragon's Fire",
        "name_pt": "Fogo do Dragão",
        "set_name_en": "Adventures in the Forgotten Realms",
        "quantity": 3,
        "quality": "NM",
        "language": "PT",
        "rarity": "C",
        "color": "R",
        "extras": None,
        "acquisition_price": None,
        "acquired_at": None,
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
    app.dependency_overrides[get_current_user] = _fake_user
    return app


NERDZ_HTML = """
<html>
<head><title>Pedido #9117259 | Nerdz Cards</title></head>
<body>
<div class="panel-body panel-order--number">
    <h3>#9117259</h3>
    <div align="center"><i>25/08/2025 17:01</i></div>
</div>
<article class="panel-order--content layout-standard">
    <div class="row">
        <div class="col-xs-12 col-sm-6 col-md-6">
            <p>
                <span class="bold">3x</span> <a class="link-produto" href="#">
                    <span class="bold">Fogo do Dragão</span>  / Dragon's Fire
                    <font class="input-infoaux">(Código: AFR<b>139</b>)</font>
                </a>
            </p>
        </div>
        <div class="col-xs-6 col-sm-3">
            <p>R$ 0,20 (unid.)</p>
        </div>
    </div>
    <div class="row m-top-xs">
        <div class="col-xs-6 col-sm-3">
            <img src="AFR_C.gif" title="Adventures in the Forgotten Realms"
                 class="icon icon-edicao" height="21">
        </div>
        <div class="col-xs-3 col-sm-1">
            <img alt="Português" src="pt.svg">&nbsp;PT
        </div>
        <div class="col-xs-3 col-sm-1">
            <div class="icon_qualid" title="Praticamente Nova (NM)">NM</div>
        </div>
    </div>
</article>
</body>
</html>
""".strip()


class TestImportPreview:
    def test_preview_with_nerdz_html(self):
        mock_repo = MagicMock()
        entry = _make_entry()
        mock_repo.list_collection.return_value = [entry]

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/import-preview",
            files=[("files", ("order.html", NERDZ_HTML, "text/html"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_files"] == 1
        assert data["total_orders"] == 1
        assert data["total_items_parsed"] == 1
        assert data["total_items_matched"] == 1
        assert len(data["matches"]) == 1
        match = data["matches"][0]
        assert match["confidence"] == 1.0
        assert match["collection_entry_id"] == 1

    def test_preview_unknown_format(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        html = "<html><head><title>Unknown</title></head><body></body></html>"
        resp = client.post(
            "/api/v1/purchases/import-preview",
            files=[("files", ("test.html", html, "text/html"))],
        )
        assert resp.status_code == 400

    def test_preview_no_files(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        # FastAPI will reject missing required files with 422
        resp = client.post("/api/v1/purchases/import-preview")
        assert resp.status_code == 422

    def test_preview_non_html_file(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/import-preview",
            files=[("files", ("test.txt", "hello", "text/plain"))],
        )
        assert resp.status_code == 400

    def test_preview_overwrite_existing_false(self):
        mock_repo = MagicMock()
        entry = _make_entry(acquisition_price=Decimal("5.00"))
        mock_repo.list_collection.return_value = [entry]

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/import-preview?overwrite_existing=false",
            files=[("files", ("order.html", NERDZ_HTML, "text/html"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        # Match is excluded because entry already has price
        assert data["total_items_matched"] == 0

    def test_preview_overwrite_existing_true(self):
        mock_repo = MagicMock()
        entry = _make_entry(acquisition_price=Decimal("5.00"))
        mock_repo.list_collection.return_value = [entry]

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/import-preview?overwrite_existing=true",
            files=[("files", ("order.html", NERDZ_HTML, "text/html"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items_matched"] == 1
        assert data["matches"][0]["already_has_price"] is True

    def test_preview_empty_collection(self):
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = []

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/import-preview",
            files=[("files", ("order.html", NERDZ_HTML, "text/html"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items_matched"] == 0
        assert data["total_items_unmatched"] == 1

    def test_preview_sealed_product(self):
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = []
        sealed_html = """
        <html><head><title>Pedido #5282134 | Nerdz Cards</title></head>
        <body>
        <div class="panel-body panel-order--number">
            <h3>#5282134</h3><div><i>01/01/2025 10:00</i></div>
        </div>
        <article class="panel-order--content layout-standard">
            <div class="row">
                <div class="col-xs-12 col-sm-6">
                    <p><span class="bold">1x</span>
                        <a class="link-produto" href="#">
                            <span class="bold">Kit Inicial</span>
                        </a>
                    </p>
                </div>
            </div>
        </article>
        </body></html>
        """
        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/import-preview",
            files=[("files", ("sealed.html", sealed_html, "text/html"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items_parsed"] == 0
        assert data["total_items_matched"] == 0

    def test_preview_multiple_files(self):
        mock_repo = MagicMock()
        entry = _make_entry()
        mock_repo.list_collection.return_value = [entry]

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/import-preview",
            files=[
                ("files", ("order1.html", NERDZ_HTML, "text/html")),
                ("files", ("order2.html", NERDZ_HTML, "text/html")),
            ],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_files"] == 2
        assert data["total_orders"] == 2


class TestApplyPurchases:
    def test_apply_happy_path(self):
        mock_repo = MagicMock()
        entry = _make_entry()
        mock_repo.get_collection_entry.return_value = entry
        mock_repo.update_collection_entry.return_value = entry

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/apply",
            json={
                "matches": [
                    {
                        "collection_entry_id": 1,
                        "acquisition_price": "0.20",
                        "acquired_at": "2025-08-25",
                        "overwrite": False,
                    }
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_applied"] == 1
        assert data["total_skipped"] == 0
        mock_repo.update_collection_entry.assert_called_once()

    def test_apply_skip_existing_price(self):
        mock_repo = MagicMock()
        entry = _make_entry(acquisition_price=Decimal("5.00"))
        mock_repo.get_collection_entry.return_value = entry

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/apply",
            json={
                "matches": [
                    {
                        "collection_entry_id": 1,
                        "acquisition_price": "0.20",
                        "acquired_at": "2025-08-25",
                        "overwrite": False,
                    }
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_applied"] == 0
        assert data["total_skipped"] == 1
        assert "Already has price" in data["skipped"][0]["reason"]

    def test_apply_overwrite_existing(self):
        mock_repo = MagicMock()
        entry = _make_entry(acquisition_price=Decimal("5.00"))
        mock_repo.get_collection_entry.return_value = entry
        mock_repo.update_collection_entry.return_value = entry

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/apply",
            json={
                "matches": [
                    {
                        "collection_entry_id": 1,
                        "acquisition_price": "0.20",
                        "acquired_at": "2025-08-25",
                        "overwrite": True,
                    }
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_applied"] == 1

    def test_apply_empty_matches(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/apply",
            json={"matches": []},
        )
        assert resp.status_code == 400

    def test_apply_wrong_user(self):
        mock_repo = MagicMock()
        entry = _make_entry(user_id="other_user")
        mock_repo.get_collection_entry.return_value = entry

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/apply",
            json={
                "matches": [
                    {
                        "collection_entry_id": 1,
                        "acquisition_price": "0.20",
                        "overwrite": False,
                    }
                ]
            },
        )
        assert resp.status_code == 403

    def test_apply_not_found(self):
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = None

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/apply",
            json={
                "matches": [
                    {
                        "collection_entry_id": 999,
                        "acquisition_price": "0.20",
                        "overwrite": False,
                    }
                ]
            },
        )
        assert resp.status_code == 404

    def test_apply_multiple(self):
        mock_repo = MagicMock()
        entry1 = _make_entry(id=1)
        entry2 = _make_entry(id=2, name_en="Terror of the Peaks")
        mock_repo.get_collection_entry.side_effect = [entry1, entry2]
        mock_repo.update_collection_entry.side_effect = [entry1, entry2]

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/apply",
            json={
                "matches": [
                    {
                        "collection_entry_id": 1,
                        "acquisition_price": "0.20",
                        "acquired_at": "2025-08-25",
                    },
                    {
                        "collection_entry_id": 2,
                        "acquisition_price": "179.90",
                        "acquired_at": "2025-08-25",
                    },
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_applied"] == 2

    def test_file_too_large(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        # Create a file just over 5MB
        large_content = "x" * (5 * 1024 * 1024 + 1)
        resp = client.post(
            "/api/v1/purchases/import-preview",
            files=[("files", ("big.html", large_content, "text/html"))],
        )
        assert resp.status_code == 400
        assert "5MB" in resp.json()["detail"]

    def test_apply_invalid_price_is_skipped(self):
        """Invalid price format should be skipped, not crash the endpoint."""
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/apply",
            json={
                "matches": [
                    {
                        "collection_entry_id": 1,
                        "acquisition_price": "not-a-number",
                        "acquired_at": "2025-08-25",
                    }
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_applied"] == 0
        assert data["total_skipped"] == 1
        assert "Invalid price" in data["skipped"][0]["reason"]

    def test_apply_invalid_date_is_ignored(self):
        """Invalid date format should result in acquired_at=None, not an error."""
        mock_repo = MagicMock()
        entry = _make_entry()
        mock_repo.get_collection_entry.return_value = entry
        mock_repo.update_collection_entry.return_value = entry

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/apply",
            json={
                "matches": [
                    {
                        "collection_entry_id": 1,
                        "acquisition_price": "9.90",
                        "acquired_at": "bad-date",
                    }
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_applied"] == 1
        # acquired_at should be None since the date was invalid
        assert data["applied"][0]["acquired_at"] is None

    def test_apply_uses_transaction(self):
        """Verify that apply wraps updates in repo.transaction() for atomicity."""
        mock_repo = MagicMock()
        entry1 = _make_entry(id=1)
        entry2 = _make_entry(id=2, name_en="Lightning Bolt")
        mock_repo.get_collection_entry.side_effect = [entry1, entry2]
        mock_repo.update_collection_entry.return_value = entry1

        # Make transaction() return a context manager that yields a session
        mock_session = MagicMock()

        @contextmanager
        def fake_transaction():
            yield mock_session

        mock_repo.transaction = fake_transaction

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/apply",
            json={
                "matches": [
                    {
                        "collection_entry_id": 1,
                        "acquisition_price": "0.20",
                        "acquired_at": "2025-08-25",
                    },
                    {
                        "collection_entry_id": 2,
                        "acquisition_price": "1.50",
                        "acquired_at": "2025-08-25",
                    },
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_applied"] == 2
        # Both update calls should have received the transaction session
        calls = mock_repo.update_collection_entry.call_args_list
        assert len(calls) == 2
        for call in calls:
            assert call.kwargs.get("session") is mock_session

    def test_apply_no_entry_id_silently_skipped(self):
        """Matches without collection_entry_id should be silently skipped."""
        mock_repo = MagicMock()

        @contextmanager
        def fake_transaction():
            yield MagicMock()

        mock_repo.transaction = fake_transaction

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/apply",
            json={
                "matches": [
                    {
                        "acquisition_price": "0.20",
                        "acquired_at": "2025-08-25",
                    }
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_applied"] == 0
        assert data["total_skipped"] == 0

    def test_apply_mixed_valid_and_invalid(self):
        """Mix of valid, invalid-price, and skip-existing entries."""
        mock_repo = MagicMock()
        entry_valid = _make_entry(id=1)
        entry_has_price = _make_entry(id=2, acquisition_price=Decimal("5.00"))
        mock_repo.get_collection_entry.side_effect = [entry_valid, entry_has_price]
        mock_repo.update_collection_entry.return_value = entry_valid

        mock_session = MagicMock()

        @contextmanager
        def fake_transaction():
            yield mock_session

        mock_repo.transaction = fake_transaction

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/purchases/apply",
            json={
                "matches": [
                    {  # invalid price -- skipped
                        "collection_entry_id": 99,
                        "acquisition_price": "abc",
                    },
                    {  # valid entry
                        "collection_entry_id": 1,
                        "acquisition_price": "3.50",
                        "acquired_at": "2025-01-01",
                    },
                    {  # has existing price, no overwrite -- skipped
                        "collection_entry_id": 2,
                        "acquisition_price": "2.00",
                        "overwrite": False,
                    },
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_applied"] == 1
        assert data["total_skipped"] == 2  # invalid price + already has price

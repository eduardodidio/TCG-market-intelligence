"""Integration tests for collection CRUD operations (F89).

Full-stack tests: real SQLite DB, FastAPI TestClient, auth override.
Covers batch add, single edit, single delete, bulk edit, bulk delete, IDOR.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.app import create_app
from src.api.deps import get_db
from src.auth.dependencies import require_auth_or_api_key
from src.database.models import UserCollectionRow
from src.database.repository import Repository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_A = "user-a-id"
USER_B = "user-b-id"


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_crud.db"
    return Repository(db_url=f"sqlite:///{db_path}")


def _make_client(repo: Repository, user_id: str) -> TestClient:
    """Create a TestClient with auth overridden to return the given user_id."""
    app = create_app()

    def override_db():
        yield repo

    def override_auth():
        return user_id

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_auth_or_api_key] = override_auth

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def client_a(repo):
    return _make_client(repo, USER_A)


@pytest.fixture()
def client_b(repo):
    return _make_client(repo, USER_B)


def _seed_entries(repo: Repository, user_id: str, count: int) -> list[int]:
    """Directly insert collection entries and return their IDs."""
    ids = []
    with Session(repo.engine) as session:
        for i in range(count):
            row = UserCollectionRow(
                user_id=user_id,
                name_en=f"Card {i + 1}",
                set_code="m21",
                collector_number=str(100 + i),
                quantity=1,
                quality="NM",
                language="EN",
            )
            session.add(row)
            session.flush()
            ids.append(row.id)
        session.commit()
    return ids


# ---------------------------------------------------------------------------
# Tests: Batch Add -> Verify in DB
# ---------------------------------------------------------------------------


class TestBatchAddFlow:
    def test_batch_parse_and_add(self, client_a, repo):
        # 1. Parse text
        text = "2 Lightning Bolt [M21]\n1 Counterspell\n3 Sol Ring [CMR] NM EN"
        resp = client_a.post("/api/v1/collection/batch/parse", json={"text": text})
        assert resp.status_code == 200
        data = resp.json()["data"]
        entries = data["entries"]
        assert len(entries) == 3
        assert entries[0]["name"] == "Lightning Bolt"
        assert entries[0]["quantity"] == 2

        # 2. Add valid entries
        body = [
            {"name_en": e["name"], "set_code": e["set_code"], "quantity": e["quantity"]}
            for e in entries
            if not e.get("error")
        ]
        resp = client_a.post("/api/v1/collection/batch", json={"entries": body})
        assert resp.status_code == 200
        result = resp.json()["data"]
        assert result["added"] == 3

        # 3. Verify in DB
        with Session(repo.engine) as session:
            rows = session.query(UserCollectionRow).filter_by(user_id=USER_A).all()
            assert len(rows) == 3
            names = {r.name_en for r in rows}
            assert "Lightning Bolt" in names
            assert "Sol Ring" in names


# ---------------------------------------------------------------------------
# Tests: Single Edit
# ---------------------------------------------------------------------------


class TestSingleEdit:
    def test_edit_quantity(self, client_a, repo):
        ids = _seed_entries(repo, USER_A, 1)
        entry_id = ids[0]

        resp = client_a.patch(f"/api/v1/collection/{entry_id}", json={"quantity": 5})
        assert resp.status_code == 200
        assert resp.json()["data"]["quantity"] == 5

        # Verify in DB
        with Session(repo.engine) as session:
            row = session.get(UserCollectionRow, entry_id)
            assert row.quantity == 5

    def test_edit_quality(self, client_a, repo):
        ids = _seed_entries(repo, USER_A, 1)
        entry_id = ids[0]

        resp = client_a.patch(f"/api/v1/collection/{entry_id}", json={"quality": "SP"})
        assert resp.status_code == 200
        assert resp.json()["data"]["quality"] == "SP"

    def test_edit_extras_foil_sets_is_foil(self, client_a, repo):
        ids = _seed_entries(repo, USER_A, 1)
        entry_id = ids[0]

        resp = client_a.patch(f"/api/v1/collection/{entry_id}", json={"extras": "foil"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["extras"] == "foil"
        assert data["is_foil"] is True

    def test_edit_nonexistent_returns_404(self, client_a):
        resp = client_a.patch("/api/v1/collection/99999", json={"quantity": 1})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Single Delete
# ---------------------------------------------------------------------------


class TestSingleDelete:
    def test_delete_entry(self, client_a, repo):
        ids = _seed_entries(repo, USER_A, 2)

        resp = client_a.delete(f"/api/v1/collection/{ids[0]}")
        assert resp.status_code == 204

        # Verify only 1 remains
        with Session(repo.engine) as session:
            remaining = session.query(UserCollectionRow).filter_by(user_id=USER_A).count()
            assert remaining == 1

    def test_delete_nonexistent_returns_404(self, client_a):
        resp = client_a.delete("/api/v1/collection/99999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Bulk Edit
# ---------------------------------------------------------------------------


class TestBulkEdit:
    def test_bulk_update_condition(self, client_a, repo):
        ids = _seed_entries(repo, USER_A, 4)
        target_ids = ids[:3]

        resp = client_a.patch(
            "/api/v1/collection/bulk",
            json={"ids": target_ids, "updates": {"quality": "HP"}},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["affected"] == 3

        # Verify in DB
        with Session(repo.engine) as session:
            for eid in target_ids:
                row = session.get(UserCollectionRow, eid)
                assert row.quality == "HP"
            # Unchanged entry
            row = session.get(UserCollectionRow, ids[3])
            assert row.quality == "NM"

    def test_bulk_update_language(self, client_a, repo):
        ids = _seed_entries(repo, USER_A, 2)

        resp = client_a.patch(
            "/api/v1/collection/bulk",
            json={"ids": ids, "updates": {"language": "JP"}},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["affected"] == 2


# ---------------------------------------------------------------------------
# Tests: Bulk Delete
# ---------------------------------------------------------------------------


class TestBulkDelete:
    def test_bulk_delete_multiple(self, client_a, repo):
        ids = _seed_entries(repo, USER_A, 5)
        to_delete = ids[:3]

        resp = client_a.post(
            "/api/v1/collection/bulk-delete",
            json={"ids": to_delete},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] == 3

        # Verify only 2 remain
        with Session(repo.engine) as session:
            remaining = session.query(UserCollectionRow).filter_by(user_id=USER_A).count()
            assert remaining == 2


# ---------------------------------------------------------------------------
# Tests: IDOR Protection
# ---------------------------------------------------------------------------


class TestIDORProtection:
    def test_user_b_cannot_edit_user_a_entry(self, client_b, repo):
        ids = _seed_entries(repo, USER_A, 1)

        resp = client_b.patch(f"/api/v1/collection/{ids[0]}", json={"quantity": 99})
        assert resp.status_code == 403

    def test_user_b_cannot_delete_user_a_entry(self, client_b, repo):
        ids = _seed_entries(repo, USER_A, 1)

        resp = client_b.delete(f"/api/v1/collection/{ids[0]}")
        assert resp.status_code == 403

    def test_user_b_cannot_bulk_edit_user_a_entries(self, client_b, repo):
        ids = _seed_entries(repo, USER_A, 2)

        resp = client_b.patch(
            "/api/v1/collection/bulk",
            json={"ids": ids, "updates": {"quality": "D"}},
        )
        assert resp.status_code == 403

    def test_user_b_cannot_bulk_delete_user_a_entries(self, client_b, repo):
        ids = _seed_entries(repo, USER_A, 2)

        resp = client_b.post(
            "/api/v1/collection/bulk-delete",
            json={"ids": ids},
        )
        assert resp.status_code == 403

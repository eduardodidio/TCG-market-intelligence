from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db
from src.api.routers.collect import router

app = FastAPI()
app.include_router(router)


def _mock_get_db():
    return MagicMock()


app.dependency_overrides[get_db] = _mock_get_db

client = TestClient(app)


class TestBackfillEndpoint:
    @patch("src.api.routers.collect.asyncio.create_task")
    def test_accepts_valid_request(self, mock_create_task: MagicMock) -> None:
        mock_create_task.return_value = AsyncMock()
        response = client.post(
            "/collect/backfill",
            json={"set": "dmr", "limit": 5, "history_days": 30},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["status"] == "started"
        assert body["data"]["job_id"]
        assert "dmr" in body["data"]["message"]
        assert "meta" in body
        assert body["errors"] == []

    @patch("src.api.routers.collect.asyncio.create_task")
    def test_defaults_applied(self, mock_create_task: MagicMock) -> None:
        mock_create_task.return_value = AsyncMock()
        response = client.post("/collect/backfill", json={"set": "dmr"})
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["status"] == "started"

    def test_rejects_missing_set_field(self) -> None:
        response = client.post("/collect/backfill", json={})
        assert response.status_code == 422

    def test_rejects_empty_body(self) -> None:
        response = client.post("/collect/backfill")
        assert response.status_code == 422


class TestUpdateEndpoint:
    @patch("src.api.routers.collect.asyncio.create_task")
    def test_accepts_valid_request_with_set(self, mock_create_task: MagicMock) -> None:
        mock_create_task.return_value = AsyncMock()
        response = client.post("/collect/update", json={"set": "dmr"})
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["status"] == "started"
        assert body["data"]["job_id"]
        assert "dmr" in body["data"]["message"]

    @patch("src.api.routers.collect.asyncio.create_task")
    def test_accepts_request_without_set(self, mock_create_task: MagicMock) -> None:
        mock_create_task.return_value = AsyncMock()
        response = client.post("/collect/update", json={})
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["status"] == "started"
        assert "all sets" in body["data"]["message"]

    @patch("src.api.routers.collect.asyncio.create_task")
    def test_accepts_empty_body(self, mock_create_task: MagicMock) -> None:
        mock_create_task.return_value = AsyncMock()
        response = client.post(
            "/collect/update",
            content="{}",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200

    @patch("src.api.routers.collect.asyncio.create_task")
    def test_envelope_format(self, mock_create_task: MagicMock) -> None:
        mock_create_task.return_value = AsyncMock()
        response = client.post("/collect/update", json={})
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert "errors" in body
        assert "request_id" in body["meta"]

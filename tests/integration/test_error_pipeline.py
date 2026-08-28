"""Integration tests for the full error capture pipeline (F85-T08).

Verifies: exception -> DB + JSONL -> API query -> cleanup.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.deps import get_current_user, get_db
from src.api.routers.admin import router as admin_router
from src.database.repository import Repository
from src.domain.models import User
from src.errors.logger import ErrorLogger, make_db_sink, make_jsonl_sink
from src.errors.retention import cleanup_db, cleanup_jsonl


def _make_admin_user(user_id: int = 1) -> User:
    return User(
        id=user_id,
        email="admin@test.com",
        display_name="Admin",
        auth_provider="email",
        is_active=True,
        is_admin=True,
    )


def _create_pipeline_app(
    repo: Repository,
    jsonl_path: str,
    admin_user: User,
) -> FastAPI:
    """Create a FastAPI app wired with DB+JSONL error sinks and admin endpoints."""
    db_sink = make_db_sink(repo)
    jsonl_sink = make_jsonl_sink(jsonl_path)
    error_logger = ErrorLogger(sinks=[db_sink, jsonl_sink])

    app = FastAPI()
    app.state.error_logger = error_logger

    # Admin router for querying errors
    app.include_router(admin_router, prefix="/api/v1")

    # Override dependencies
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: admin_user

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Test endpoints
    @app.get("/ok")
    def ok_endpoint():
        return {"status": "ok"}

    @app.get("/crash")
    def crash_endpoint():
        raise ValueError("pipeline boom")

    @app.get("/crash-runtime")
    def crash_runtime():
        raise RuntimeError("runtime failure")

    # Exception handlers (mirrors production app.py)
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        if exc.status_code >= 500:
            try:
                el = getattr(request.app.state, "error_logger", None)
                if el:
                    ctx = {
                        "request_method": request.method,
                        "request_path": str(request.url.path),
                        "request_user_id": None,
                        "request_id": request_id,
                        "params": dict(request.query_params),
                    }
                    el.capture(exc, request_context=ctx)
            except Exception:
                pass
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": str(exc.detail), "request_id": request_id},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        try:
            el = getattr(request.app.state, "error_logger", None)
            if el:
                ctx = {
                    "request_method": request.method,
                    "request_path": str(request.url.path),
                    "request_user_id": None,
                    "request_id": request_id,
                    "params": dict(request.query_params),
                }
                el.capture(exc, request_context=ctx)
        except Exception:
            pass
        return JSONResponse(
            status_code=500,
            content={"error": "internal error", "request_id": request_id},
        )

    return app


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_pipeline.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def admin_user(repo):
    user = _make_admin_user()
    user_row = repo.create_user(email=user.email, display_name=user.display_name)
    repo.update_user(user_row.id, is_admin=1)
    return user


@pytest.fixture()
def jsonl_path(tmp_path):
    return str(tmp_path / "errors.jsonl")


@pytest.fixture()
def client(repo, jsonl_path, admin_user):
    app = _create_pipeline_app(repo, jsonl_path, admin_user)
    return TestClient(app, raise_server_exceptions=False)


class TestEndToEndCapture:
    """Exception -> captured in DB -> queryable via API."""

    def test_exception_appears_in_error_list(self, client):
        # Trigger an unhandled exception
        resp = client.get("/crash")
        assert resp.status_code == 500

        # Query via admin API
        list_resp = client.get("/api/v1/admin/errors")
        assert list_resp.status_code == 200
        body = list_resp.json()
        assert body["meta"]["total"] == 1
        assert len(body["data"]) == 1

        entry = body["data"][0]
        assert entry["error_type"] == "ValueError"
        assert entry["message"] == "pipeline boom"

    def test_detail_includes_traceback(self, client):
        client.get("/crash")

        list_resp = client.get("/api/v1/admin/errors")
        error_id = list_resp.json()["data"][0]["id"]

        detail_resp = client.get(f"/api/v1/admin/errors/{error_id}")
        assert detail_resp.status_code == 200
        data = detail_resp.json()["data"]
        assert data["traceback"] is not None
        assert len(data["traceback"]) > 0
        assert "ValueError" in data["traceback"]

    def test_request_context_captured(self, client):
        client.get("/crash?foo=bar")

        list_resp = client.get("/api/v1/admin/errors")
        error_id = list_resp.json()["data"][0]["id"]

        detail_resp = client.get(f"/api/v1/admin/errors/{error_id}")
        data = detail_resp.json()["data"]
        assert data["request_method"] == "GET"
        assert data["request_path"] == "/crash"
        assert data["request_id"] is not None
        # request_params is parsed to dict by the detail endpoint
        assert data["request_params"] == {"foo": "bar"}

    def test_multiple_errors_accumulate(self, client):
        client.get("/crash")
        client.get("/crash-runtime")

        list_resp = client.get("/api/v1/admin/errors")
        body = list_resp.json()
        assert body["meta"]["total"] == 2

        types = {e["error_type"] for e in body["data"]}
        assert types == {"ValueError", "RuntimeError"}


class TestJsonlVerification:
    """JSONL file contains the error after capture."""

    def test_jsonl_written_with_matching_id(self, client, jsonl_path):
        client.get("/crash")

        # Get error ID from API
        list_resp = client.get("/api/v1/admin/errors")
        api_error_id = list_resp.json()["data"][0]["id"]

        # Read JSONL file
        assert os.path.exists(jsonl_path)
        with open(jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1

        jsonl_entry = json.loads(lines[0])
        assert jsonl_entry["id"] == api_error_id
        assert jsonl_entry["error_type"] == "ValueError"
        assert jsonl_entry["request_method"] == "GET"
        assert jsonl_entry["request_path"] == "/crash"

    def test_multiple_errors_append_to_jsonl(self, client, jsonl_path):
        client.get("/crash")
        client.get("/crash-runtime")

        with open(jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 2

        types = {json.loads(line)["error_type"] for line in lines}
        assert types == {"ValueError", "RuntimeError"}

    def test_ok_endpoint_does_not_write_jsonl(self, client, jsonl_path):
        client.get("/ok")
        assert not os.path.exists(jsonl_path)


class TestCleanupPipeline:
    """Insert old errors, run cleanup, verify removed from both stores."""

    def test_cleanup_removes_old_db_entries(self, repo, client):
        # Insert an old error directly
        old_error = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC) - timedelta(days=60),
            "level": "ERROR",
            "error_type": "OldError",
            "message": "ancient failure",
            "traceback": "...",
            "module": "src.test",
            "function": "old_fn",
            "line": 1,
            "request_method": None,
            "request_path": None,
            "request_user_id": None,
            "request_id": None,
            "request_params": None,
            "extra": None,
        }
        repo.insert_error_log(old_error)

        # Trigger a fresh error
        client.get("/crash")

        # Verify both exist
        list_resp = client.get("/api/v1/admin/errors")
        assert list_resp.json()["meta"]["total"] == 2

        # Run cleanup with 30-day retention
        removed = cleanup_db(repo, max_age_days=30, max_entries=10000)
        assert removed >= 1

        # Verify old error is gone, fresh one remains
        list_resp = client.get("/api/v1/admin/errors")
        body = list_resp.json()
        assert body["meta"]["total"] == 1
        assert body["data"][0]["error_type"] == "ValueError"

    def test_cleanup_removes_old_jsonl_entries(self, client, jsonl_path):
        # Write an old entry directly to JSONL
        old_entry = {
            "id": str(uuid.uuid4()),
            "timestamp": (datetime.now(UTC) - timedelta(days=60)).isoformat(),
            "level": "ERROR",
            "error_type": "OldJsonlError",
            "message": "old jsonl entry",
        }
        os.makedirs(os.path.dirname(jsonl_path) or ".", exist_ok=True)
        with open(jsonl_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(old_entry) + "\n")

        # Trigger a fresh error (appends to JSONL)
        client.get("/crash")

        with open(jsonl_path, "r", encoding="utf-8") as f:
            assert len(f.readlines()) == 2

        # Run cleanup
        removed = cleanup_jsonl(jsonl_path, max_age_days=30, max_entries=10000)
        assert removed >= 1

        # Verify old entry removed, fresh one remains
        with open(jsonl_path, "r", encoding="utf-8") as f:
            remaining = f.readlines()
        assert len(remaining) == 1
        entry = json.loads(remaining[0])
        assert entry["error_type"] == "ValueError"

"""Tests for error capture integration in FastAPI exception handlers (F85-T05)."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.errors.logger import ErrorLogger, make_jsonl_sink


def _create_test_app(error_logger: ErrorLogger | None = None) -> FastAPI:
    """Create a minimal FastAPI app with error capture wired in.

    Avoids the full production app (scheduler, Liga, providers) by building
    a small standalone app that mirrors the production exception handlers.
    """
    import uuid

    from fastapi.responses import JSONResponse

    app = FastAPI()

    if error_logger is not None:
        app.state.error_logger = error_logger

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.get("/ok")
    def ok_endpoint():
        return {"status": "ok"}

    @app.get("/crash")
    def crash_endpoint():
        raise ValueError("boom")

    @app.get("/http-500")
    def http_500_endpoint():
        raise HTTPException(status_code=500, detail="server broke")

    @app.get("/http-404")
    def http_404_endpoint():
        raise HTTPException(status_code=404, detail="not found")

    @app.get("/http-503")
    def http_503_endpoint():
        raise HTTPException(status_code=503, detail="service unavailable")

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        # Capture server errors (5xx) in error logger
        if exc.status_code >= 500:
            try:
                el = getattr(request.app.state, "error_logger", None)
                if el:
                    user_id = getattr(getattr(request.state, "user", None), "id", None)
                    ctx = {
                        "request_method": request.method,
                        "request_path": str(request.url.path),
                        "request_user_id": user_id,
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

        # Capture in error logger
        try:
            el = getattr(request.app.state, "error_logger", None)
            if el:
                user_id = getattr(getattr(request.state, "user", None), "id", None)
                ctx = {
                    "request_method": request.method,
                    "request_path": str(request.url.path),
                    "request_user_id": user_id,
                    "request_id": request_id,
                    "params": dict(request.query_params),
                }
                el.capture(exc, request_context=ctx)
        except Exception:
            pass  # Never let error logging break error response

        return JSONResponse(
            status_code=500,
            content={"error": "internal error", "request_id": request_id},
        )

    return app


@pytest.fixture()
def captured_errors() -> list[dict]:
    """Accumulator for captured error dicts."""
    return []


@pytest.fixture()
def error_logger(captured_errors: list[dict]) -> ErrorLogger:
    """ErrorLogger with a simple in-memory list sink."""

    def list_sink(error_dict: dict) -> None:
        captured_errors.append(error_dict)

    return ErrorLogger(sinks=[list_sink])


@pytest.fixture()
def client(error_logger: ErrorLogger) -> TestClient:
    """TestClient with error capture wired in."""
    app = _create_test_app(error_logger)
    return TestClient(app, raise_server_exceptions=False)


class TestUnhandledExceptionCapture:
    """Unhandled exceptions (generic handler) are captured."""

    def test_value_error_is_captured(self, client, captured_errors):
        resp = client.get("/crash")
        assert resp.status_code == 500
        assert len(captured_errors) == 1
        err = captured_errors[0]
        assert err["error_type"] == "ValueError"
        assert err["message"] == "boom"

    def test_request_context_included(self, client, captured_errors):
        resp = client.get("/crash?foo=bar")
        assert resp.status_code == 500
        assert len(captured_errors) == 1
        err = captured_errors[0]
        assert err["request_method"] == "GET"
        assert err["request_path"] == "/crash"
        assert err["request_id"] is not None
        params = json.loads(err["request_params"])
        assert params["foo"] == "bar"

    def test_user_id_none_for_unauthenticated(self, client, captured_errors):
        client.get("/crash")
        assert captured_errors[0]["request_user_id"] is None

    def test_response_still_returns_500(self, client):
        resp = client.get("/crash")
        assert resp.status_code == 500
        body = resp.json()
        assert body["error"] == "internal error"
        assert "request_id" in body


class TestHttpExceptionCapture:
    """HTTP exceptions: only 5xx are captured."""

    def test_http_500_is_captured(self, client, captured_errors):
        resp = client.get("/http-500")
        assert resp.status_code == 500
        assert len(captured_errors) == 1
        err = captured_errors[0]
        assert err["error_type"] == "HTTPException"
        assert err["request_path"] == "/http-500"

    def test_http_503_is_captured(self, client, captured_errors):
        resp = client.get("/http-503")
        assert resp.status_code == 503
        assert len(captured_errors) == 1
        assert captured_errors[0]["request_path"] == "/http-503"

    def test_http_404_is_not_captured(self, client, captured_errors):
        resp = client.get("/http-404")
        assert resp.status_code == 404
        assert len(captured_errors) == 0

    def test_ok_endpoint_not_captured(self, client, captured_errors):
        resp = client.get("/ok")
        assert resp.status_code == 200
        assert len(captured_errors) == 0


class TestJsonlSinkIntegration:
    """JSONL file is written when exceptions occur."""

    def test_jsonl_written_after_exception(self, tmp_path):
        jsonl_path = str(tmp_path / "errors.jsonl")
        logger = ErrorLogger(sinks=[make_jsonl_sink(jsonl_path)])
        app = _create_test_app(logger)
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get("/crash")
        assert resp.status_code == 500

        assert os.path.exists(jsonl_path)
        with open(jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["error_type"] == "ValueError"
        assert entry["request_method"] == "GET"
        assert entry["request_path"] == "/crash"

    def test_multiple_errors_append(self, tmp_path):
        jsonl_path = str(tmp_path / "errors.jsonl")
        logger = ErrorLogger(sinks=[make_jsonl_sink(jsonl_path)])
        app = _create_test_app(logger)
        client = TestClient(app, raise_server_exceptions=False)

        client.get("/crash")
        client.get("/http-500")

        with open(jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 2


class TestNoErrorLoggerGraceful:
    """App works fine when error_logger is not initialized."""

    def test_no_error_logger_still_returns_500(self):
        app = _create_test_app(error_logger=None)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/crash")
        assert resp.status_code == 500

    def test_no_error_logger_http_500_still_returns(self):
        app = _create_test_app(error_logger=None)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/http-500")
        assert resp.status_code == 500


class TestGetErrorLoggerDependency:
    """get_error_logger dependency returns logger from app state."""

    def test_returns_logger_when_set(self):
        from src.api.deps import get_error_logger

        mock_request = MagicMock(spec=Request)
        mock_logger = MagicMock(spec=ErrorLogger)
        mock_request.app.state.error_logger = mock_logger

        result = get_error_logger(mock_request)
        assert result is mock_logger

    def test_returns_none_when_not_set(self):
        from src.api.deps import get_error_logger

        mock_request = MagicMock(spec=Request)
        # Simulate no error_logger attribute on state
        del mock_request.app.state.error_logger

        result = get_error_logger(mock_request)
        assert result is None


class TestScanErrorCapture:
    """Scan collector captures errors via global logger."""

    def test_scan_captures_via_global_logger(self):
        from src.errors.logger import get_global_error_logger, set_global_error_logger

        captured: list[dict] = []

        def list_sink(error_dict: dict) -> None:
            captured.append(error_dict)

        logger = ErrorLogger(sinks=[list_sink])
        set_global_error_logger(logger)

        try:
            # Simulate what scan.py does
            exc = RuntimeError("scan failed")
            error_logger = get_global_error_logger()
            if error_logger:
                error_logger.capture(exc, extra={"scan_id": 42, "context": "scan_loop"})

            assert len(captured) == 1
            assert captured[0]["error_type"] == "RuntimeError"
            assert captured[0]["message"] == "scan failed"
            extra = json.loads(captured[0]["extra"])
            assert extra["scan_id"] == 42
            assert extra["context"] == "scan_loop"
        finally:
            set_global_error_logger(None)

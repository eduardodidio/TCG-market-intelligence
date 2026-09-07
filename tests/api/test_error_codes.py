"""Tests for the error codes module (F102-T01)."""

from __future__ import annotations

import os

import pytest
from fastapi import HTTPException

from src.api.error_codes import ErrorCode, api_error


class TestErrorCodeConstants:
    """Verify that all error codes are unique non-empty strings."""

    def _all_codes(self) -> list[str]:
        """Collect every string constant from ErrorCode."""
        return [
            v for k, v in vars(ErrorCode).items() if not k.startswith("_") and isinstance(v, str)
        ]

    def test_all_codes_are_strings(self):
        codes = self._all_codes()
        assert len(codes) > 0
        for code in codes:
            assert isinstance(code, str)
            assert len(code) > 0

    def test_all_codes_are_unique(self):
        codes = self._all_codes()
        assert len(codes) == len(set(codes)), "Duplicate error codes found"

    def test_known_codes_exist(self):
        assert ErrorCode.AUTH_INVALID_CREDENTIALS == "AUTH_INVALID_CREDENTIALS"
        assert ErrorCode.AUTH_TOKEN_EXPIRED == "AUTH_TOKEN_EXPIRED"
        assert ErrorCode.CREDIT_INSUFFICIENT == "CREDIT_INSUFFICIENT"
        assert ErrorCode.RESOURCE_NOT_FOUND == "RESOURCE_NOT_FOUND"
        assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCode.INTERNAL_ERROR == "INTERNAL_ERROR"
        assert ErrorCode.EXTERNAL_TIMEOUT == "EXTERNAL_TIMEOUT"
        assert ErrorCode.AUTHZ_ADMIN_REQUIRED == "AUTHZ_ADMIN_REQUIRED"

    def test_code_count_minimum(self):
        """We should have at least 20 distinct error codes."""
        codes = self._all_codes()
        assert len(codes) >= 20


class TestApiErrorHelper:
    """Verify that api_error() produces correct HTTPExceptions."""

    def test_basic_error(self):
        exc = api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Card not found")
        assert isinstance(exc, HTTPException)
        assert exc.status_code == 404
        assert exc.detail["code"] == "RESOURCE_NOT_FOUND"
        assert exc.detail["message"] == "Card not found"

    def test_error_with_field(self):
        exc = api_error(
            422,
            ErrorCode.VALIDATION_ERROR,
            "Invalid email",
            field="body.email",
        )
        assert exc.status_code == 422
        assert exc.detail["field"] == "body.email"

    def test_error_without_field_omits_field(self):
        exc = api_error(400, ErrorCode.VALIDATION_ERROR, "Bad")
        # field should not be in the dict, or should be None
        assert exc.detail.get("field") is None

    def test_error_preserves_status_code(self):
        for status in [400, 401, 403, 404, 409, 422, 500, 502, 503, 504]:
            exc = api_error(status, ErrorCode.INTERNAL_ERROR, "test")
            assert exc.status_code == status

    def test_detail_is_dict(self):
        exc = api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Not found")
        assert isinstance(exc.detail, dict)
        assert "code" in exc.detail
        assert "message" in exc.detail


class TestExceptionHandlerIntegration:
    """Verify the updated exception handler in app.py works with both
    dict-based and string-based detail formats."""

    @pytest.fixture()
    def client(self):
        os.environ["TCG_SCHEDULER_DISABLED"] = "1"
        from fastapi.testclient import TestClient

        from src.api.app import create_app

        app = create_app()
        return TestClient(app, raise_server_exceptions=False)

    def test_string_detail_returns_http_code(self, client):
        """Old-style string detail should produce HTTP_xxx codes."""
        resp = client.get("/api/v1/nonexistent-path-for-testing")
        assert resp.status_code in (404, 405)
        data = resp.json()
        assert data["errors"][0]["code"].startswith("HTTP_")

    def test_dict_detail_extracts_code(self, client):
        """Dict detail from api_error() should produce the domain error code.

        We add a temporary route that raises api_error().
        """
        from src.api.app import create_app

        os.environ["TCG_SCHEDULER_DISABLED"] = "1"
        app = create_app()

        @app.get("/test-error-code")
        def test_route():
            raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Card not found")

        from fastapi.testclient import TestClient

        test_client = TestClient(app, raise_server_exceptions=False)

        resp = test_client.get("/test-error-code")
        assert resp.status_code == 404
        data = resp.json()
        assert data["errors"][0]["code"] == "RESOURCE_NOT_FOUND"
        assert data["errors"][0]["message"] == "Card not found"

    def test_string_detail_backwards_compat(self, client):
        """String details continue to produce the old HTTP_xxx code format."""
        from src.api.app import create_app

        os.environ["TCG_SCHEDULER_DISABLED"] = "1"
        app = create_app()

        @app.get("/test-string-error")
        def test_route():
            raise HTTPException(status_code=401, detail="Not authenticated")

        from fastapi.testclient import TestClient

        test_client = TestClient(app, raise_server_exceptions=False)

        resp = test_client.get("/test-string-error")
        assert resp.status_code == 401
        data = resp.json()
        assert data["errors"][0]["code"] == "HTTP_401"
        assert data["errors"][0]["message"] == "Not authenticated"

    def test_dict_detail_with_field(self, client):
        """Dict detail with field key should include the field in the response."""
        from src.api.app import create_app

        os.environ["TCG_SCHEDULER_DISABLED"] = "1"
        app = create_app()

        @app.get("/test-field-error")
        def test_route():
            raise api_error(422, ErrorCode.VALIDATION_ERROR, "Too long", field="body.name")

        from fastapi.testclient import TestClient

        test_client = TestClient(app, raise_server_exceptions=False)

        resp = test_client.get("/test-field-error")
        assert resp.status_code == 422
        data = resp.json()
        assert data["errors"][0]["code"] == "VALIDATION_ERROR"
        assert data["errors"][0]["field"] == "body.name"

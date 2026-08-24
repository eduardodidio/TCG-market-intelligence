"""Tests for MYP typed exception hierarchy (F45-T01)."""

from __future__ import annotations

from src.providers.myp.exceptions import (
    MypError,
    NotFoundError,
    RateLimitError,
    ServerError,
)


class TestMypExceptionHierarchy:
    """Verify inheritance, attributes, and str representation."""

    def test_myp_error_is_runtime_error(self):
        err = MypError("boom", url="https://x.com", status_code=418, attempts=2)
        assert isinstance(err, RuntimeError)
        assert str(err) == "boom"
        assert err.url == "https://x.com"
        assert err.status_code == 418
        assert err.attempts == 2

    def test_not_found_error_is_myp_error(self):
        err = NotFoundError("gone", url="/card/1", status_code=404, attempts=1)
        assert isinstance(err, MypError)
        assert isinstance(err, RuntimeError)
        assert err.status_code == 404

    def test_rate_limit_error_is_myp_error(self):
        err = RateLimitError("slow down", url="/search", status_code=429, attempts=3)
        assert isinstance(err, MypError)
        assert err.status_code == 429
        assert err.attempts == 3

    def test_server_error_is_myp_error(self):
        err = ServerError("internal", url="/page", status_code=500, attempts=2)
        assert isinstance(err, MypError)
        assert err.status_code == 500

    def test_default_attributes(self):
        err = MypError("simple")
        assert err.url == ""
        assert err.status_code == 0
        assert err.attempts == 1

"""Root conftest — shared fixtures for all tests."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _ensure_jwt_secret(monkeypatch):
    """Ensure TCG_JWT_SECRET is set so auth-dependent code doesn't crash."""
    if "TCG_JWT_SECRET" not in os.environ:
        monkeypatch.setenv("TCG_JWT_SECRET", "test-secret-for-unit-tests")


@pytest.fixture(autouse=True)
def _clear_api_key_for_tests(monkeypatch):
    """Remove TCG_API_KEY during tests so dev-mode auth bypass is active.

    Without this, tests that don't provide the API key header fail with 401
    when TCG_API_KEY happens to be set in the developer's environment.
    """
    monkeypatch.delenv("TCG_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def _clear_database_url_for_tests(monkeypatch):
    """Remove DATABASE_URL during tests so tests don't hit the production Neon DB.

    Tests that need a specific DB should set their own DATABASE_URL or
    TCG_DATABASE_URL via patch.dict or monkeypatch.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)


@pytest.fixture(autouse=True)
def _reset_repo_singleton():
    """Reset the deps.py Repository singleton between tests.

    Without this, the singleton from a previous test may hold a connection
    to the wrong database.
    """
    import src.api.deps as deps

    deps._repo_singleton = None
    yield
    deps._repo_singleton = None

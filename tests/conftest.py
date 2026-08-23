"""Root conftest — shared fixtures for all tests."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _ensure_jwt_secret(monkeypatch):
    """Ensure TCG_JWT_SECRET is set so auth-dependent code doesn't crash."""
    if "TCG_JWT_SECRET" not in os.environ:
        monkeypatch.setenv("TCG_JWT_SECRET", "test-secret-for-unit-tests")

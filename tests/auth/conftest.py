"""Shared fixtures for auth tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _set_jwt_secret(monkeypatch):
    """Ensure TCG_JWT_SECRET is always set for auth tests."""
    monkeypatch.setenv("TCG_JWT_SECRET", "test-secret-for-unit-tests")

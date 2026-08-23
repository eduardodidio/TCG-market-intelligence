"""Tests for src.config module."""

import os
from unittest.mock import patch

from src.config import get_db_url


class TestGetDbUrl:
    def test_returns_default_when_env_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove TCG_DATABASE_URL if present
            os.environ.pop("TCG_DATABASE_URL", None)
            assert get_db_url() == "sqlite:///tcg_market.db"

    def test_returns_env_value_when_set(self):
        with patch.dict(os.environ, {"TCG_DATABASE_URL": "sqlite:///custom.db"}):
            assert get_db_url() == "sqlite:///custom.db"

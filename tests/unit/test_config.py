"""Tests for src.config module."""

import os
from unittest.mock import patch

from src.config import _ensure_psycopg2_dialect, get_db_url


class TestGetDbUrl:
    def test_returns_default_when_env_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DATABASE_URL", None)
            os.environ.pop("TCG_DATABASE_URL", None)
            assert get_db_url() == "sqlite:///tcg_market.db"

    def test_returns_env_value_when_set(self):
        with patch.dict(os.environ, {"TCG_DATABASE_URL": "sqlite:///custom.db"}, clear=True):
            os.environ.pop("DATABASE_URL", None)
            assert get_db_url() == "sqlite:///custom.db"

    def test_database_url_takes_priority(self):
        with patch.dict(
            os.environ,
            {"DATABASE_URL": "sqlite:///primary.db", "TCG_DATABASE_URL": "sqlite:///fallback.db"},
            clear=True,
        ):
            assert get_db_url() == "sqlite:///primary.db"

    def test_postgresql_url_gets_psycopg2_dialect(self):
        with patch.dict(
            os.environ,
            {"DATABASE_URL": "postgresql://user:pass@host/db"},
            clear=True,
        ):
            assert get_db_url() == "postgresql+psycopg2://user:pass@host/db"


class TestEnsurePsycopg2Dialect:
    def test_plain_postgresql(self):
        assert _ensure_psycopg2_dialect("postgresql://u:p@h/d") == "postgresql+psycopg2://u:p@h/d"

    def test_already_psycopg2(self):
        url = "postgresql+psycopg2://u:p@h/d"
        assert _ensure_psycopg2_dialect(url) == url

    def test_sqlite_unchanged(self):
        assert _ensure_psycopg2_dialect("sqlite:///test.db") == "sqlite:///test.db"

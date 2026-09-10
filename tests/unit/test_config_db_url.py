"""Tests for get_db_url() priority logic."""

from __future__ import annotations

from src.config import get_db_url


class TestGetDbUrl:
    def test_database_url_takes_priority(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://neon:5432/db")
        monkeypatch.setenv("TCG_DATABASE_URL", "sqlite:///old.db")
        assert get_db_url() == "postgresql://neon:5432/db"

    def test_tcg_database_url_fallback(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("TCG_DATABASE_URL", "sqlite:///custom.db")
        assert get_db_url() == "sqlite:///custom.db"

    def test_default_sqlite(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("TCG_DATABASE_URL", raising=False)
        monkeypatch.setattr("os.path.isdir", lambda p: False)
        assert get_db_url() == "sqlite:///tcg_market.db"

    def test_database_url_empty_skipped(self, monkeypatch):
        """Empty string should NOT be treated as a valid URL."""
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.delenv("TCG_DATABASE_URL", raising=False)
        monkeypatch.setattr("os.path.isdir", lambda p: False)
        assert get_db_url() == "sqlite:///tcg_market.db"

    def test_render_data_dir_detection(self, monkeypatch):
        """When /data exists, use the Render persistent disk path."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("TCG_DATABASE_URL", raising=False)
        monkeypatch.setattr("os.path.isdir", lambda p: p == "/data")
        assert get_db_url() == "sqlite:////data/tcg_market.db"

    def test_database_url_wins_over_render_dir(self, monkeypatch):
        """Explicit DATABASE_URL takes priority even if /data exists."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://neon/prod")
        monkeypatch.setattr("os.path.isdir", lambda p: True)
        assert get_db_url() == "postgresql://neon/prod"

    def test_tcg_url_empty_also_skipped(self, monkeypatch):
        """Both empty env vars should fall through to default."""
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.setenv("TCG_DATABASE_URL", "")
        monkeypatch.setattr("os.path.isdir", lambda p: False)
        assert get_db_url() == "sqlite:///tcg_market.db"

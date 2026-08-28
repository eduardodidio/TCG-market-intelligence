"""Tests for src/errors/retention.py and config helpers."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from src.config import get_error_log_dir, get_error_max_age_days, get_error_max_entries
from src.errors.retention import cleanup_db, cleanup_jsonl

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(days_ago: int, msg: str = "err") -> dict:
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {"timestamp": ts.isoformat(), "message": msg}


def _write_jsonl(path, entries: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def _read_jsonl(path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


class TestConfigDefaults:
    def test_error_log_dir_default(self, monkeypatch):
        monkeypatch.delenv("TCG_ERROR_LOG_DIR", raising=False)
        assert get_error_log_dir() == "logs/errors"

    def test_error_max_age_days_default(self, monkeypatch):
        monkeypatch.delenv("TCG_ERROR_MAX_AGE_DAYS", raising=False)
        assert get_error_max_age_days() == 30

    def test_error_max_entries_default(self, monkeypatch):
        monkeypatch.delenv("TCG_ERROR_MAX_ENTRIES", raising=False)
        assert get_error_max_entries() == 10000


class TestConfigOverride:
    def test_error_log_dir_override(self, monkeypatch):
        monkeypatch.setenv("TCG_ERROR_LOG_DIR", "/tmp/custom_errors")
        assert get_error_log_dir() == "/tmp/custom_errors"

    def test_error_max_age_days_override(self, monkeypatch):
        monkeypatch.setenv("TCG_ERROR_MAX_AGE_DAYS", "7")
        assert get_error_max_age_days() == 7

    def test_error_max_entries_override(self, monkeypatch):
        monkeypatch.setenv("TCG_ERROR_MAX_ENTRIES", "500")
        assert get_error_max_entries() == 500


# ---------------------------------------------------------------------------
# cleanup_jsonl
# ---------------------------------------------------------------------------


class TestCleanupJsonl:
    def test_missing_file_returns_zero(self, tmp_path):
        result = cleanup_jsonl(str(tmp_path / "nonexistent.jsonl"), 30, 10000)
        assert result == 0

    def test_empty_file_returns_zero(self, tmp_path):
        f = tmp_path / "empty.jsonl"
        f.write_text("")
        result = cleanup_jsonl(str(f), 30, 10000)
        assert result == 0

    def test_max_entries_keeps_newest(self, tmp_path):
        entries = [_make_entry(i, f"msg-{i}") for i in range(20)]
        f = tmp_path / "errors.jsonl"
        _write_jsonl(str(f), entries)

        removed = cleanup_jsonl(str(f), max_age_days=365, max_entries=10)
        assert removed == 10

        kept = _read_jsonl(str(f))
        assert len(kept) == 10
        # Newest entries have smallest days_ago (0..9), verify sorted desc
        for i in range(len(kept) - 1):
            assert kept[i]["timestamp"] >= kept[i + 1]["timestamp"]

    def test_age_filter_removes_old(self, tmp_path):
        recent = [_make_entry(i) for i in range(5)]  # 0-4 days ago
        old = [_make_entry(40 + i) for i in range(5)]  # 40-44 days ago
        f = tmp_path / "errors.jsonl"
        _write_jsonl(str(f), recent + old)

        removed = cleanup_jsonl(str(f), max_age_days=30, max_entries=10000)
        assert removed == 5

        kept = _read_jsonl(str(f))
        assert len(kept) == 5

    def test_combined_age_and_max_entries(self, tmp_path):
        # 15 recent (0-14 days), 5 old (40-44 days)
        entries = [_make_entry(i) for i in range(15)] + [_make_entry(40 + i) for i in range(5)]
        f = tmp_path / "errors.jsonl"
        _write_jsonl(str(f), entries)

        removed = cleanup_jsonl(str(f), max_age_days=30, max_entries=10)
        # 5 removed by age, then 5 removed by max_entries cap
        assert removed == 10

        kept = _read_jsonl(str(f))
        assert len(kept) == 10

    def test_no_removal_needed(self, tmp_path):
        entries = [_make_entry(i) for i in range(5)]
        f = tmp_path / "errors.jsonl"
        _write_jsonl(str(f), entries)

        removed = cleanup_jsonl(str(f), max_age_days=30, max_entries=10000)
        assert removed == 0

        kept = _read_jsonl(str(f))
        assert len(kept) == 5

    def test_malformed_entries_kept(self, tmp_path):
        f = tmp_path / "errors.jsonl"
        with open(str(f), "w") as fh:
            fh.write(json.dumps(_make_entry(0)) + "\n")
            fh.write('{"no_timestamp": true}\n')  # valid JSON, no timestamp
            fh.write(json.dumps(_make_entry(1)) + "\n")

        removed = cleanup_jsonl(str(f), max_age_days=30, max_entries=10000)
        assert removed == 0

        kept = _read_jsonl(str(f))
        assert len(kept) == 3

    def test_atomic_write(self, tmp_path):
        """Verify that the original file is replaced atomically (no tmp files left)."""
        entries = [_make_entry(i) for i in range(20)]
        f = tmp_path / "errors.jsonl"
        _write_jsonl(str(f), entries)

        cleanup_jsonl(str(f), max_age_days=365, max_entries=5)

        # No leftover tmp files
        remaining = list(tmp_path.iterdir())
        assert len(remaining) == 1
        assert remaining[0].name == "errors.jsonl"


# ---------------------------------------------------------------------------
# cleanup_db
# ---------------------------------------------------------------------------


class TestCleanupDb:
    def test_delegates_to_repo_and_sums(self):
        repo = MagicMock()
        repo.delete_error_logs_before.return_value = 3
        repo.delete_error_logs_excess.return_value = 2

        total = cleanup_db(repo, max_age_days=30, max_entries=1000)

        assert total == 5
        repo.delete_error_logs_before.assert_called_once()
        repo.delete_error_logs_excess.assert_called_once_with(max_entries=1000)

    def test_zero_when_nothing_to_remove(self):
        repo = MagicMock()
        repo.delete_error_logs_before.return_value = 0
        repo.delete_error_logs_excess.return_value = 0

        total = cleanup_db(repo, max_age_days=30, max_entries=1000)
        assert total == 0

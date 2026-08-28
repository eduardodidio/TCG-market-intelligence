"""Unit tests for the error-cleanup CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli.main import cli


@pytest.fixture()
def runner():
    return CliRunner()


def _common_patches(tmp_path, db_url=None, cleanup_db_rv=0, cleanup_jsonl_rv=0):
    """Return a dict of common patches for the error-cleanup command."""
    _db_url = db_url or f"sqlite:///{tmp_path / 'test.db'}"
    return {
        "src.config.get_db_url": patch("src.config.get_db_url", return_value=_db_url),
        "src.config.get_error_log_dir": patch(
            "src.config.get_error_log_dir", return_value=str(tmp_path)
        ),
        "src.config.get_error_max_age_days": patch(
            "src.config.get_error_max_age_days", return_value=30
        ),
        "src.config.get_error_max_entries": patch(
            "src.config.get_error_max_entries", return_value=10000
        ),
        "src.errors.retention.cleanup_db": patch(
            "src.errors.retention.cleanup_db", return_value=cleanup_db_rv
        ),
        "src.errors.retention.cleanup_jsonl": patch(
            "src.errors.retention.cleanup_jsonl", return_value=cleanup_jsonl_rv
        ),
        "src.database.repository.Repository": patch("src.database.repository.Repository"),
    }


class TestErrorCleanupHappyPath:
    """Run cleanup, verify entries removed (mocked)."""

    def test_cleanup_removes_entries(self, runner, tmp_path):
        patches = _common_patches(tmp_path, cleanup_db_rv=5, cleanup_jsonl_rv=3)

        with (
            patches["src.config.get_db_url"],
            patches["src.config.get_error_log_dir"],
            patches["src.config.get_error_max_age_days"],
            patches["src.config.get_error_max_entries"],
            patches["src.errors.retention.cleanup_db"] as mock_db,
            patches["src.errors.retention.cleanup_jsonl"] as mock_jsonl,
            patches["src.database.repository.Repository"] as mock_repo_cls,
        ):
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo

            result = runner.invoke(cli, ["error-cleanup"])

            assert result.exit_code == 0, result.output
            assert "Database entries removed: 5" in result.output
            assert "JSONL entries removed:    3" in result.output

            mock_db.assert_called_once_with(mock_repo, 30, 10000)
            mock_jsonl.assert_called_once()


class TestErrorCleanupDryRun:
    """Run with --dry-run, verify no entries removed."""

    def test_dry_run_shows_counts(self, runner, tmp_path):
        import uuid
        from datetime import datetime, timezone

        from sqlalchemy.orm import Session

        from src.database.models import ErrorLogRow
        from src.database.repository import Repository

        # Create a real temp database with error rows
        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        repo = Repository(db_url=db_url)

        with Session(repo.engine) as session:
            for i in range(7):
                session.add(
                    ErrorLogRow(
                        id=str(uuid.uuid4()),
                        timestamp=datetime.now(timezone.utc),
                        level="ERROR",
                        error_type="TestError",
                        message=f"error {i}",
                    )
                )
            session.commit()

        # Create a fake JSONL file with some lines
        jsonl_path = tmp_path / "errors.jsonl"
        jsonl_path.write_text('{"ts":1}\n{"ts":2}\n{"ts":3}\n')

        with (
            patch("src.config.get_error_log_dir", return_value=str(tmp_path)),
            patch("src.config.get_error_max_age_days", return_value=30),
            patch("src.config.get_error_max_entries", return_value=10000),
            patch("src.errors.retention.cleanup_db") as mock_db,
            patch("src.errors.retention.cleanup_jsonl") as mock_jsonl,
        ):
            result = runner.invoke(cli, ["error-cleanup", "--db", db_url, "--dry-run"])

            assert result.exit_code == 0, result.output
            assert "DRY RUN" in result.output
            assert "Database entries: 7" in result.output
            assert "JSONL entries:    3" in result.output

            # Cleanup functions should NOT be called
            mock_db.assert_not_called()
            mock_jsonl.assert_not_called()

    def test_dry_run_no_jsonl_file(self, runner, tmp_path):
        """Dry run when JSONL file does not exist shows 0."""
        from src.database.repository import Repository

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        Repository(db_url=db_url)  # create tables

        with (
            patch("src.config.get_error_log_dir", return_value=str(tmp_path)),
            patch("src.config.get_error_max_age_days", return_value=30),
            patch("src.config.get_error_max_entries", return_value=10000),
            patch("src.errors.retention.cleanup_db"),
            patch("src.errors.retention.cleanup_jsonl"),
        ):
            result = runner.invoke(cli, ["error-cleanup", "--db", db_url, "--dry-run"])

            assert result.exit_code == 0, result.output
            assert "Database entries: 0" in result.output
            assert "JSONL entries:    0" in result.output


class TestErrorCleanupCustomOptions:
    """--max-age-days and --max-entries are respected."""

    def test_custom_age_and_entries(self, runner, tmp_path):
        patches = _common_patches(tmp_path, cleanup_db_rv=10, cleanup_jsonl_rv=2)

        with (
            patches["src.config.get_db_url"],
            patches["src.config.get_error_log_dir"],
            patches["src.config.get_error_max_age_days"],
            patches["src.config.get_error_max_entries"],
            patches["src.errors.retention.cleanup_db"] as mock_db,
            patches["src.errors.retention.cleanup_jsonl"] as mock_jsonl,
            patches["src.database.repository.Repository"] as mock_repo_cls,
        ):
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo

            result = runner.invoke(
                cli,
                ["error-cleanup", "--max-age-days=7", "--max-entries=100"],
            )

            assert result.exit_code == 0, result.output
            assert "max_age_days=7" in result.output
            assert "max_entries=100" in result.output

            # Verify custom values passed through
            mock_db.assert_called_once_with(mock_repo, 7, 100)
            jsonl_call_args = mock_jsonl.call_args
            assert jsonl_call_args[0][1] == 7  # max_age_days
            assert jsonl_call_args[0][2] == 100  # max_entries


class TestErrorCleanupEmptyState:
    """No errors to clean up, reports 0 removed."""

    def test_zero_removed(self, runner, tmp_path):
        patches = _common_patches(tmp_path, cleanup_db_rv=0, cleanup_jsonl_rv=0)

        with (
            patches["src.config.get_db_url"],
            patches["src.config.get_error_log_dir"],
            patches["src.config.get_error_max_age_days"],
            patches["src.config.get_error_max_entries"],
            patches["src.errors.retention.cleanup_db"],
            patches["src.errors.retention.cleanup_jsonl"],
            patches["src.database.repository.Repository"] as mock_repo_cls,
        ):
            mock_repo_cls.return_value = MagicMock()

            result = runner.invoke(cli, ["error-cleanup"])

            assert result.exit_code == 0, result.output
            assert "Database entries removed: 0" in result.output
            assert "JSONL entries removed:    0" in result.output


class TestErrorCleanupDbOption:
    """--db option overrides default database URL."""

    def test_db_option_passed_to_repository(self, runner, tmp_path):
        custom_db = f"sqlite:///{tmp_path / 'custom.db'}"
        patches = _common_patches(tmp_path, cleanup_db_rv=0, cleanup_jsonl_rv=0)

        with (
            patches["src.config.get_error_log_dir"],
            patches["src.config.get_error_max_age_days"],
            patches["src.config.get_error_max_entries"],
            patches["src.errors.retention.cleanup_db"],
            patches["src.errors.retention.cleanup_jsonl"],
            patches["src.database.repository.Repository"] as mock_repo_cls,
        ):
            mock_repo_cls.return_value = MagicMock()

            result = runner.invoke(cli, ["error-cleanup", "--db", custom_db])

            assert result.exit_code == 0, result.output
            mock_repo_cls.assert_called_once_with(db_url=custom_db)

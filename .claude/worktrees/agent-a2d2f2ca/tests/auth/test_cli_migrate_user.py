"""Tests for the migrate-user CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.cli.main import cli


class TestMigrateUser:
    def test_migrate_with_entries(self):
        runner = CliRunner()
        with patch("src.database.repository.Repository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.migrate_collection_user.return_value = 5
            MockRepo.return_value = mock_repo

            result = runner.invoke(cli, ["migrate-user", "--new-id", "42"])
            assert result.exit_code == 0
            assert "Migrated 5 collection entries" in result.output

    def test_migrate_no_entries(self):
        runner = CliRunner()
        with patch("src.database.repository.Repository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.migrate_collection_user.return_value = 0
            MockRepo.return_value = mock_repo

            result = runner.invoke(cli, ["migrate-user", "--new-id", "42"])
            assert result.exit_code == 0
            assert "No collection entries found" in result.output

    def test_migrate_custom_old_id(self):
        runner = CliRunner()
        with patch("src.database.repository.Repository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.migrate_collection_user.return_value = 3
            MockRepo.return_value = mock_repo

            result = runner.invoke(
                cli, ["migrate-user", "--old-id", "legacy_user", "--new-id", "99"]
            )
            assert result.exit_code == 0
            mock_repo.migrate_collection_user.assert_called_once_with("legacy_user", "99")

    def test_missing_new_id_shows_error(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["migrate-user"])
        assert result.exit_code != 0
        assert "Missing" in result.output or "required" in result.output.lower()

"""Tests for the reset-password CLI command (F102-T02)."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli.main import cli


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def mock_repo():
    repo = MagicMock()
    return repo


class TestResetPasswordCLI:
    """Test the 'reset-password' CLI command."""

    def test_happy_path_auto_password(self, runner, mock_repo):
        """When user exists, the command generates a temp password and prints it."""
        user_row = MagicMock()
        user_row.id = 42
        user_row.email = "user@example.com"
        mock_repo.get_user_by_email.return_value = user_row
        mock_repo.reset_user_password.return_value = user_row

        with patch("src.database.repository.Repository", return_value=mock_repo):
            result = runner.invoke(
                cli,
                ["reset-password", "--email", "user@example.com", "--db", "sqlite:///test.db"],
            )

        assert result.exit_code == 0
        assert "Password reset for user@example.com" in result.output
        assert "Temporary password:" in result.output
        assert "Expires at:" in result.output
        assert "User must change password on next login." in result.output
        # Verify reset_user_password was called
        mock_repo.reset_user_password.assert_called_once()
        call_args = mock_repo.reset_user_password.call_args
        assert call_args[0][0] == "user@example.com"

    def test_user_not_found(self, runner, mock_repo):
        """When the user doesn't exist, the command prints an error and exits 1."""
        mock_repo.get_user_by_email.return_value = None

        with patch("src.database.repository.Repository", return_value=mock_repo):
            result = runner.invoke(
                cli,
                [
                    "reset-password",
                    "--email",
                    "nonexistent@example.com",
                    "--db",
                    "sqlite:///test.db",
                ],
            )

        assert result.exit_code == 1
        assert "Error: User not found" in result.output

    def test_custom_password(self, runner, mock_repo):
        """When --password is provided, it should use that instead of generating one."""
        user_row = MagicMock()
        user_row.id = 1
        user_row.email = "test@test.com"
        mock_repo.get_user_by_email.return_value = user_row
        mock_repo.reset_user_password.return_value = user_row

        with patch("src.database.repository.Repository", return_value=mock_repo):
            result = runner.invoke(
                cli,
                [
                    "reset-password",
                    "--email",
                    "test@test.com",
                    "--password",
                    "MyCustomPass123",
                    "--db",
                    "sqlite:///test.db",
                ],
            )

        assert result.exit_code == 0
        assert "MyCustomPass123" in result.output

    def test_custom_expires_hours(self, runner, mock_repo):
        """The --expires-hours flag should set a custom expiry."""
        user_row = MagicMock()
        user_row.id = 1
        user_row.email = "test@test.com"
        mock_repo.get_user_by_email.return_value = user_row
        mock_repo.reset_user_password.return_value = user_row

        with patch("src.database.repository.Repository", return_value=mock_repo):
            result = runner.invoke(
                cli,
                [
                    "reset-password",
                    "--email",
                    "test@test.com",
                    "--expires-hours",
                    "48",
                    "--db",
                    "sqlite:///test.db",
                ],
            )

        assert result.exit_code == 0
        # Verify the expiry was passed with correct hours
        call_args = mock_repo.reset_user_password.call_args
        expires_at = call_args[0][2]  # Third positional arg
        # It should be approximately 48 hours from now
        expected = datetime.now() + timedelta(hours=48)
        assert abs((expires_at - expected).total_seconds()) < 5

    def test_generated_password_is_valid(self, runner, mock_repo):
        """The generated password should be verifiable against the stored hash."""
        user_row = MagicMock()
        user_row.id = 1
        user_row.email = "test@test.com"
        mock_repo.get_user_by_email.return_value = user_row
        mock_repo.reset_user_password.return_value = user_row

        captured_hash = []
        original_reset = mock_repo.reset_user_password

        def capture_reset(email, pw_hash, expires_at):
            captured_hash.append(pw_hash)
            return original_reset(email, pw_hash, expires_at)

        mock_repo.reset_user_password = capture_reset

        with patch("src.database.repository.Repository", return_value=mock_repo):
            result = runner.invoke(
                cli,
                [
                    "reset-password",
                    "--email",
                    "test@test.com",
                    "--db",
                    "sqlite:///test.db",
                ],
            )

        assert result.exit_code == 0
        # Extract the temp password from output
        temp_password = None
        for line in result.output.split("\n"):
            if "Temporary password:" in line:
                temp_password = line.split(":")[-1].strip()
                break

        assert temp_password is not None
        # Verify it matches the hash
        from src.auth.passwords import verify_password

        assert len(captured_hash) == 1
        assert verify_password(temp_password, captured_hash[0])

    def test_email_option_is_required(self, runner):
        """The --email option is required."""
        result = runner.invoke(cli, ["reset-password", "--db", "sqlite:///test.db"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "Error" in result.output

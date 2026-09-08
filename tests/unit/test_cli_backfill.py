"""Tests for CLI backfill-portfolio command."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.cli.main import cli

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_repo(user_rows=None):
    """Return a mock Repository with a mock engine and session support."""
    repo = MagicMock()
    repo.engine = MagicMock()
    return repo


def _make_user_row(uid, is_active=1):
    """Build a mock UserRow."""
    user = MagicMock()
    user.id = uid
    user.is_active = is_active
    return user


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


class TestBackfillPortfolioParsing:
    def test_default_options(self):
        """Command accepts defaults and runs."""
        runner = CliRunner()
        with (
            patch("src.database.repository.Repository") as mock_repo_cls,
            patch(
                "src.collectors.portfolio_backfill.backfill_acquisition_prices",
                return_value={"updated": 0, "skipped": 0, "total": 0},
            ),
            patch(
                "src.collectors.portfolio_backfill.backfill_portfolio_snapshots",
                return_value={"days_filled": 0, "days_skipped": 0},
            ),
            patch(
                "src.collectors.portfolio_snapshot.take_snapshot",
                return_value={
                    "user_id": "user1",
                    "date": date.today(),
                    "value": Decimal("0"),
                    "priced_count": 0,
                    "total_cards": 0,
                },
            ),
        ):
            mock_repo_cls.return_value = _mock_repo()
            # Provide a user-id so we don't need to query the DB for users
            result = runner.invoke(
                cli,
                ["backfill-portfolio", "--db", "sqlite:///test.db", "--user-id", "user1"],
            )

        assert result.exit_code == 0, result.output
        assert "Backfill complete" in result.output

    def test_days_option(self):
        """--days is passed correctly."""
        runner = CliRunner()
        with (
            patch("src.database.repository.Repository") as mock_repo_cls,
            patch(
                "src.collectors.portfolio_backfill.backfill_acquisition_prices",
                return_value={"updated": 5, "skipped": 1, "total": 6},
            ),
            patch(
                "src.collectors.portfolio_backfill.backfill_portfolio_snapshots",
                return_value={"days_filled": 7, "days_skipped": 0},
            ) as mock_snap_backfill,
            patch(
                "src.collectors.portfolio_snapshot.take_snapshot",
                return_value={
                    "user_id": "u1",
                    "date": date.today(),
                    "value": Decimal("100"),
                    "priced_count": 5,
                    "total_cards": 6,
                },
            ),
        ):
            mock_repo_cls.return_value = _mock_repo()
            result = runner.invoke(
                cli,
                [
                    "backfill-portfolio",
                    "--db",
                    "sqlite:///test.db",
                    "--user-id",
                    "u1",
                    "--days",
                    "7",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_snap_backfill.assert_called_once()
        # Verify the days argument was passed
        call_args = mock_snap_backfill.call_args
        assert call_args[0][2] == 7 or call_args.kwargs.get("days") == 7 or call_args[0][-1] == 7

    def test_skip_prices_flag(self):
        """--skip-prices skips acquisition price backfill."""
        runner = CliRunner()
        with (
            patch("src.database.repository.Repository") as mock_repo_cls,
            patch(
                "src.collectors.portfolio_backfill.backfill_acquisition_prices",
            ) as mock_price_backfill,
            patch(
                "src.collectors.portfolio_backfill.backfill_portfolio_snapshots",
                return_value={"days_filled": 5, "days_skipped": 0},
            ),
            patch(
                "src.collectors.portfolio_snapshot.take_snapshot",
                return_value={
                    "user_id": "u1",
                    "date": date.today(),
                    "value": Decimal("50"),
                    "priced_count": 3,
                    "total_cards": 5,
                },
            ),
        ):
            mock_repo_cls.return_value = _mock_repo()
            result = runner.invoke(
                cli,
                [
                    "backfill-portfolio",
                    "--db",
                    "sqlite:///test.db",
                    "--user-id",
                    "u1",
                    "--skip-prices",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_price_backfill.assert_not_called()
        assert "skipped" in result.output

    def test_summary_table_output(self):
        """Output includes a summary table with user info."""
        runner = CliRunner()
        with (
            patch("src.database.repository.Repository") as mock_repo_cls,
            patch(
                "src.collectors.portfolio_backfill.backfill_acquisition_prices",
                return_value={"updated": 10, "skipped": 2, "total": 12},
            ),
            patch(
                "src.collectors.portfolio_backfill.backfill_portfolio_snapshots",
                return_value={"days_filled": 28, "days_skipped": 2},
            ),
            patch(
                "src.collectors.portfolio_snapshot.take_snapshot",
                return_value={
                    "user_id": "user42",
                    "date": date.today(),
                    "value": Decimal("1234.56"),
                    "priced_count": 10,
                    "total_cards": 12,
                },
            ),
        ):
            mock_repo_cls.return_value = _mock_repo()
            result = runner.invoke(
                cli,
                [
                    "backfill-portfolio",
                    "--db",
                    "sqlite:///test.db",
                    "--user-id",
                    "user42",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "user42" in result.output
        assert "10/12" in result.output
        assert "R$ 1234.56" in result.output


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------


class TestBackfillPortfolioDryRun:
    def test_dry_run_no_db_writes(self):
        """--dry-run produces output but does NOT call backfill functions."""
        runner = CliRunner()

        mock_session = MagicMock()
        # Mock scalar calls: missing_prices=5, total_entries=10, existing_snapshots=3
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.scalar.return_value = 5

        with (
            patch("src.database.repository.Repository") as mock_repo_cls,
            patch(
                "src.collectors.portfolio_backfill.backfill_acquisition_prices",
            ) as mock_price,
            patch(
                "src.collectors.portfolio_backfill.backfill_portfolio_snapshots",
            ) as mock_snap,
            patch(
                "src.collectors.portfolio_snapshot.take_snapshot",
            ) as mock_today,
            patch("sqlalchemy.orm.Session", return_value=mock_session),
        ):
            repo = _mock_repo()
            mock_repo_cls.return_value = repo
            result = runner.invoke(
                cli,
                [
                    "backfill-portfolio",
                    "--db",
                    "sqlite:///test.db",
                    "--user-id",
                    "testuser",
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "DRY RUN" in result.output
        assert "Dry run complete" in result.output
        # Backfill functions must NOT be called
        mock_price.assert_not_called()
        mock_snap.assert_not_called()
        mock_today.assert_not_called()

    def test_dry_run_with_skip_prices(self):
        """--dry-run --skip-prices shows 'skipped' for prices."""
        runner = CliRunner()

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.scalar.return_value = 0

        with (
            patch("src.database.repository.Repository") as mock_repo_cls,
            patch("sqlalchemy.orm.Session", return_value=mock_session),
        ):
            mock_repo_cls.return_value = _mock_repo()
            result = runner.invoke(
                cli,
                [
                    "backfill-portfolio",
                    "--db",
                    "sqlite:///test.db",
                    "--user-id",
                    "u1",
                    "--dry-run",
                    "--skip-prices",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "skipped" in result.output
        assert "DRY RUN" in result.output

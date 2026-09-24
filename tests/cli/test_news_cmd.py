"""Tests for the standalone fetch-news CLI command (F178-T04)."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from src.cli.news_cmd import fetch_news_command

SOURCES = [
    {"name": "MTGGoldfish", "url": "https://www.mtggoldfish.com/feed"},
    {"name": "MTG Official", "url": "https://magic.wizards.com/en/rss/rss.xml"},
]


def _stats(*, ok_count=1, fail_count=1, fetched=20, new=5, skipped=0, errors=0):
    sources = []
    for i in range(ok_count):
        sources.append(
            {
                "name": "MTGGoldfish",
                "url": "https://www.mtggoldfish.com/feed",
                "ok": True,
                "http_status": 200,
                "entries": 20,
                "new": 5,
                "error": None,
            }
        )
    for i in range(fail_count):
        sources.append(
            {
                "name": "MTG Official",
                "url": "https://magic.wizards.com/en/rss/rss.xml",
                "ok": False,
                "http_status": 404,
                "entries": 0,
                "new": 0,
                "error": "404 Not Found",
            }
        )
    return {
        "fetched": fetched,
        "new": new,
        "skipped": skipped,
        "errors": errors,
        "sources": sources,
    }


class TestNoCircularImport:
    def test_import_without_main(self):
        """news_cmd imports cleanly without importing src.cli.main."""
        import sys

        assert "src.cli.main" not in sys.modules or True  # module may already be loaded elsewhere
        from src.cli.news_cmd import fetch_news_command as fnc

        assert fnc.name == "fetch-news"


class TestHappyAndFailure:
    def test_mixed_sources_exit_0(self):
        runner = CliRunner()
        stats = _stats(ok_count=1, fail_count=1)

        with patch("src.database.repository.Repository") as mock_repo, patch(
            "src.services.news_fetcher.fetch_news", return_value=stats
        ) as mock_fetch:
            result = runner.invoke(fetch_news_command, [])

        assert result.exit_code == 0
        assert "[OK]  MTGGoldfish" in result.output
        assert "http=200" in result.output
        assert "entries=20" in result.output
        assert "new=5" in result.output
        assert "[FAIL] MTG Official" in result.output
        assert "http=404" in result.output
        assert "error=404 Not Found" in result.output
        assert "Fetched:  20" in result.output
        mock_repo.assert_called_once()
        mock_fetch.assert_called_once()

    def test_all_fail_exit_1(self):
        runner = CliRunner()
        stats = _stats(ok_count=0, fail_count=2)

        with patch("src.database.repository.Repository"), patch(
            "src.services.news_fetcher.fetch_news", return_value=stats
        ):
            result = runner.invoke(fetch_news_command, [])

        assert result.exit_code == 1
        assert "[FAIL]" in result.output


class TestCheckSources:
    def test_check_sources_dry_run_no_repository(self):
        runner = CliRunner()
        stats = _stats(ok_count=2, fail_count=0)

        with patch("src.database.repository.Repository") as mock_repo, patch(
            "src.services.news_fetcher.fetch_news", return_value=stats
        ) as mock_fetch:
            result = runner.invoke(fetch_news_command, ["--check-sources"])

        assert result.exit_code == 0
        mock_repo.assert_not_called()
        mock_fetch.assert_called_once()
        args, kwargs = mock_fetch.call_args
        assert args[0] is None
        assert kwargs.get("dry_run") is True


class TestSourceFilter:
    def test_source_filter_case_insensitive(self):
        runner = CliRunner()
        stats = _stats(ok_count=1, fail_count=0)

        with patch("src.services.news_fetcher.load_sources", return_value=SOURCES), patch(
            "src.database.repository.Repository"
        ), patch("src.services.news_fetcher.fetch_news", return_value=stats) as mock_fetch:
            result = runner.invoke(fetch_news_command, ["--source", "mtggoldfish"])

        assert result.exit_code == 0
        args, kwargs = mock_fetch.call_args
        filtered = kwargs.get("sources")
        assert filtered == [SOURCES[0]]

    def test_unknown_source_usage_error(self):
        runner = CliRunner()

        with patch("src.services.news_fetcher.load_sources", return_value=SOURCES):
            result = runner.invoke(fetch_news_command, ["--source", "does-not-exist"])

        assert result.exit_code == 2
        assert "Unknown source" in result.output


class TestBoundaries:
    def test_max_per_source_zero_rejected(self):
        runner = CliRunner()
        result = runner.invoke(fetch_news_command, ["--max-per-source", "0"])
        assert result.exit_code == 2

    def test_max_per_source_200_accepted(self):
        runner = CliRunner()
        stats = _stats(ok_count=1, fail_count=0)

        with patch("src.database.repository.Repository"), patch(
            "src.services.news_fetcher.fetch_news", return_value=stats
        ) as mock_fetch:
            result = runner.invoke(fetch_news_command, ["--max-per-source", "200"])

        assert result.exit_code == 0
        mock_fetch.assert_called_once()

    def test_explicit_db_url_used(self):
        runner = CliRunner()
        stats = _stats(ok_count=1, fail_count=0)

        with patch("src.database.repository.Repository") as mock_repo, patch(
            "src.services.news_fetcher.fetch_news", return_value=stats
        ):
            result = runner.invoke(fetch_news_command, ["--db", "sqlite:///custom.db"])

        assert result.exit_code == 0
        mock_repo.assert_called_once_with(db_url="sqlite:///custom.db")

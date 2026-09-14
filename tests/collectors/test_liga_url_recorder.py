"""Unit tests for the shared Liga URL recording helper."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.collectors.liga_url_recorder import record_liga_url

VALID_URL = "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt&show=1"


def test_valid_url_upserts_and_returns_true():
    repo = MagicMock()

    result = record_liga_url(repo, "liga_42", VALID_URL)

    assert result is True
    repo.upsert_liga_card_url.assert_called_once_with("liga_42", VALID_URL)


def test_invalid_url_skips_upsert_and_returns_false():
    repo = MagicMock()

    result = record_liga_url(repo, "liga_42", "https://example.com/not-liga")

    assert result is False
    repo.upsert_liga_card_url.assert_not_called()


def test_none_url_skips_upsert_and_returns_false():
    repo = MagicMock()

    result = record_liga_url(repo, "liga_42", None)

    assert result is False
    repo.upsert_liga_card_url.assert_not_called()


def test_repo_error_is_swallowed_and_returns_false():
    repo = MagicMock()
    repo.upsert_liga_card_url.side_effect = RuntimeError("db down")

    result = record_liga_url(repo, "liga_42", VALID_URL)

    assert result is False

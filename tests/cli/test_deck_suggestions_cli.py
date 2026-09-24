"""Tests for the standalone process-deck-suggestions CLI command (F172-T15)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.cli.deck_suggestions import process_deck_suggestions
from src.database.repository import Repository
from src.deck_suggestions.claude_runner import ClaudeRunnerError
from src.deck_suggestions.models import DeckSuggestionRequestRow
from src.deck_suggestions.repository import create_request, ensure_table

GET_RUNNER = "src.cli.deck_suggestions.get_runner"

REPLY = json.dumps(
    {
        "deck_name": "Deck Teste",
        "strategy": "Estratégia",
        "cards": [
            {"name": "Sol Ring", "quantity": 1, "category": "Ramp", "reason": "Mana"},
            {"name": "Forest", "quantity": 20, "category": "Land", "reason": "Land"},
        ],
    }
)


class FakeRunner:
    provider = "fake"
    model = "fake-model"

    def __init__(self, response: str | Exception = REPLY, check_error: Exception | None = None):
        self.response = response
        self.check_error = check_error
        self.prompts: list[str] = []
        self.checked = False

    def check(self) -> None:
        self.checked = True
        if self.check_error is not None:
            raise self.check_error

    def run(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{tmp_path}/t.db"


def _seed(db_url: str, n: int) -> None:
    repo = Repository(db_url=db_url)
    ensure_table(repo.engine)
    for _ in range(n):
        create_request(
            repo.engine,
            user_id="user1",
            format_name="standard",
            commander_card_id=None,
            commander_name=None,
            colors="G",
            archetype="ramp",
            notes=None,
        )
    repo.engine.dispose()


def _statuses(db_url: str) -> list[str]:
    repo = Repository(db_url=db_url)
    ensure_table(repo.engine)
    with Session(repo.engine) as s:
        rows = s.execute(
            select(DeckSuggestionRequestRow.status).order_by(DeckSuggestionRequestRow.id)
        ).scalars().all()
    repo.engine.dispose()
    return list(rows)


def _invoke(args, runner=None, **patch_kwargs):
    if runner is not None:
        patch_kwargs.setdefault("return_value", runner)
    with patch(GET_RUNNER, **patch_kwargs) as get_runner:
        result = CliRunner().invoke(process_deck_suggestions, args)
    return result, get_runner


# --------------------------------------------------------------------------- happy


def test_two_pending_processed(db_url):
    _seed(db_url, 2)
    fake = FakeRunner()
    result, get_runner = _invoke(["--db", db_url], fake)

    assert result.exit_code == 0, result.output
    assert "DECK SUGGESTION PROCESSING SUMMARY" in result.output
    assert "=" * 60 in result.output
    assert "Total processed:         2" in result.output
    assert "Done:                    2" in result.output
    assert "Failed:                  0" in result.output
    assert "Retried:                 0" in result.output
    assert "Provider:                fake" in result.output
    assert "Model:                   fake-model" in result.output
    assert fake.checked
    assert len(fake.prompts) == 2
    get_runner.assert_called_once_with(None)
    assert _statuses(db_url) == ["done", "done"]


# --------------------------------------------------------------------------- edge


def test_no_pending(db_url):
    fake = FakeRunner()
    result, _ = _invoke(["--db", db_url], fake)
    assert result.exit_code == 0
    assert "No pending deck suggestions." in result.output
    assert "SUMMARY" not in result.output
    assert fake.prompts == []


def test_limit_one_leaves_one_pending(db_url):
    _seed(db_url, 2)
    result, _ = _invoke(["--db", db_url, "--limit", "1"], FakeRunner())
    assert result.exit_code == 0, result.output
    assert "Done:                    1" in result.output
    assert _statuses(db_url) == ["done", "pending"]


def test_provider_api_forwarded(db_url):
    result, get_runner = _invoke(["--db", db_url, "--provider", "api"], FakeRunner())
    assert result.exit_code == 0
    get_runner.assert_called_once_with("api")


def test_invalid_provider_rejected_by_click(db_url):
    result, get_runner = _invoke(["--db", db_url, "--provider", "gpt"], FakeRunner())
    assert result.exit_code == 2
    get_runner.assert_not_called()


def test_dry_run_counts_and_changes_nothing(db_url):
    _seed(db_url, 3)
    result, get_runner = _invoke(["--db", db_url, "--dry-run"], FakeRunner())
    assert result.exit_code == 0, result.output
    assert "Found 3 pending deck suggestion(s)." in result.output
    assert "[DRY RUN]" in result.output
    get_runner.assert_not_called()
    assert _statuses(db_url) == ["pending"] * 3


def test_dry_run_respects_limit(db_url):
    _seed(db_url, 3)
    result, _ = _invoke(["--db", db_url, "--dry-run", "--limit", "2"], FakeRunner())
    assert "Found 2 pending deck suggestion(s)." in result.output


# --------------------------------------------------------------------------- errors


def test_get_runner_config_error_exits_2_without_claiming(db_url):
    _seed(db_url, 1)
    err = ClaudeRunnerError("ANTHROPIC_API_KEY not set", transient=False)
    result, _ = _invoke(["--db", db_url, "--provider", "api"], side_effect=err)
    assert result.exit_code == 2
    assert "ANTHROPIC_API_KEY not set" in result.output
    assert _statuses(db_url) == ["pending"]


def test_check_error_exits_2_without_claiming(db_url):
    _seed(db_url, 1)
    fake = FakeRunner(check_error=ClaudeRunnerError("Claude CLI not found", transient=False))
    result, _ = _invoke(["--db", db_url], fake)
    assert result.exit_code == 2
    assert "Claude CLI not found" in result.output
    assert fake.prompts == []
    assert _statuses(db_url) == ["pending"]


def test_unknown_env_provider_exits_2(db_url):
    _seed(db_url, 1)
    err = ValueError("Unknown DECK_SUGGEST_PROVIDER 'xyz'")
    result, _ = _invoke(["--db", db_url], side_effect=err)
    assert result.exit_code == 2
    assert "xyz" in result.output
    assert _statuses(db_url) == ["pending"]


def test_real_runner_missing_binary_exits_2(db_url, monkeypatch):
    """Without patching get_runner: the real CLI runner's check() fails fast."""
    _seed(db_url, 1)
    monkeypatch.setenv("DECK_SUGGEST_CLAUDE_BIN", "definitely-not-a-claude-binary")
    monkeypatch.delenv("DECK_SUGGEST_PROVIDER", raising=False)
    result = CliRunner().invoke(process_deck_suggestions, ["--db", db_url])
    assert result.exit_code == 2
    assert "definitely-not-a-claude-binary" in result.output
    assert _statuses(db_url) == ["pending"]


def test_runner_without_check_method_still_runs(db_url):
    class NoCheckRunner:
        provider = "bare"
        model = "m"

        def run(self, prompt):
            return REPLY

    _seed(db_url, 1)
    result, _ = _invoke(["--db", db_url], NoCheckRunner())
    assert result.exit_code == 0, result.output
    assert "Done:                    1" in result.output


def test_runner_failure_exits_0_with_failed(db_url):
    _seed(db_url, 1)
    fake = FakeRunner(response=ClaudeRunnerError("bad request", transient=False))
    result, _ = _invoke(["--db", db_url], fake)
    assert result.exit_code == 0, result.output
    assert "Failed:                  1" in result.output
    assert "Done:                    0" in result.output
    assert _statuses(db_url) == ["failed"]


def test_transient_failure_counts_retried(db_url):
    _seed(db_url, 1)
    fake = FakeRunner(response=ClaudeRunnerError("timeout", transient=True))
    result, _ = _invoke(["--db", db_url], fake)
    assert result.exit_code == 0, result.output
    assert "Retried:                 1" in result.output
    assert _statuses(db_url) == ["pending"]


# --------------------------------------------------------------------------- boundary


def test_limit_zero_processes_nothing(db_url):
    _seed(db_url, 2)
    fake = FakeRunner()
    result, _ = _invoke(["--db", db_url, "--limit", "0"], fake)
    assert result.exit_code == 0
    assert "No pending deck suggestions." in result.output
    assert fake.prompts == []
    assert _statuses(db_url) == ["pending", "pending"]


def test_db_omitted_uses_get_db_url(db_url):
    _seed(db_url, 1)
    with patch("src.config.get_db_url", return_value=db_url) as get_db_url:
        result, _ = _invoke([], FakeRunner())
    assert result.exit_code == 0, result.output
    get_db_url.assert_called_once_with()
    assert _statuses(db_url) == ["done"]


def test_module_does_not_import_cli_main():
    import src.cli.deck_suggestions as mod

    source = open(mod.__file__, encoding="utf-8").read()
    assert "from src.cli.main" not in source
    assert "import src.cli.main" not in source

"""Tests for src.deck_suggestions.claude_runner (F172-T05)."""

from __future__ import annotations

import json
import os
import subprocess
from unittest.mock import patch

import httpx
import pytest
from structlog.testing import capture_logs

from src.deck_suggestions.claude_runner import (
    _CLI_BASE_ARGS,
    ANTHROPIC_VERSION,
    API_URL,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT,
    ClaudeApiRunner,
    ClaudeCliRunner,
    ClaudeRunnerError,
    get_runner,
)

SENTINEL_KEY = "sk-test-SECRET"
FAKE_BIN = "/usr/local/bin/claude"


def _claude_envelope_json(result: str = '{"deck_name": "X"}', is_error: bool = False) -> str:
    return json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": is_error,
            "result": result,
            "session_id": "abc",
        }
    )


def _claude_api_response_json(*blocks: dict) -> dict:
    content = list(blocks) or [{"type": "text", "text": '{"deck_name": "X"}'}]
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "content": content,
        "stop_reason": "end_turn",
    }


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in (
        "DECK_SUGGEST_PROVIDER",
        "DECK_SUGGEST_CLAUDE_BIN",
        "DECK_SUGGEST_MODEL",
        "DECK_SUGGEST_TIMEOUT",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------


class TestClaudeCliRunner:
    def test_happy_path_returns_result_text(self):
        with (
            patch("shutil.which", return_value=FAKE_BIN),
            patch("subprocess.run", return_value=_completed(_claude_envelope_json("hello"))) as run,
        ):
            assert ClaudeCliRunner().run("my prompt") == "hello"

        args, kwargs = run.call_args
        assert args[0] == [FAKE_BIN, *_CLI_BASE_ARGS]
        assert "--model" not in args[0]
        assert kwargs["input"] == "my prompt"
        assert kwargs["text"] is True
        assert kwargs["capture_output"] is True
        assert kwargs["shell"] is False
        assert kwargs["timeout"] == DEFAULT_TIMEOUT
        assert "my prompt" not in args[0]  # prompt only via stdin

    def test_base_args_disable_tools_and_single_turn(self):
        assert _CLI_BASE_ARGS[0] == "-p"
        assert ("--output-format", "json") == _CLI_BASE_ARGS[1:3]
        assert ("--max-turns", "1") == _CLI_BASE_ARGS[3:5]
        assert ("--tools", "") == _CLI_BASE_ARGS[5:7]

    def test_runs_in_empty_temp_dir_and_removes_it(self):
        seen = {}

        def fake_run(cmd, **kwargs):
            cwd = kwargs["cwd"]
            seen["cwd"] = cwd
            seen["exists"] = os.path.isdir(cwd)
            seen["contents"] = os.listdir(cwd)
            return _completed(_claude_envelope_json("ok"))

        with (
            patch("shutil.which", return_value=FAKE_BIN),
            patch("subprocess.run", side_effect=fake_run),
        ):
            ClaudeCliRunner().run("p")

        assert seen["exists"] is True
        assert seen["contents"] == []
        assert not os.path.exists(seen["cwd"])

    def test_temp_dir_removed_on_timeout(self):
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["cwd"] = kwargs["cwd"]
            raise subprocess.TimeoutExpired(cmd, 5)

        with (
            patch("shutil.which", return_value=FAKE_BIN),
            patch("subprocess.run", side_effect=fake_run),
        ):
            with pytest.raises(ClaudeRunnerError) as ei:
                ClaudeCliRunner(timeout=5).run("p")

        assert ei.value.transient is True
        assert "timed out after 5s" in str(ei.value)
        assert not os.path.exists(seen["cwd"])

    def test_model_env_adds_model_flag(self, monkeypatch):
        monkeypatch.setenv("DECK_SUGGEST_MODEL", "claude-opus-5-5")
        with (
            patch("shutil.which", return_value=FAKE_BIN),
            patch("subprocess.run", return_value=_completed(_claude_envelope_json())) as run,
        ):
            runner = ClaudeCliRunner()
            runner.run("p")
        assert run.call_args[0][0][-2:] == ["--model", "claude-opus-5-5"]
        assert runner.model == "claude-opus-5-5"

    def test_model_default_label_without_env(self):
        assert ClaudeCliRunner().model == "default"

    def test_bin_from_env(self, monkeypatch):
        monkeypatch.setenv("DECK_SUGGEST_CLAUDE_BIN", "C:/tools/claude.cmd")
        with (
            patch("shutil.which", return_value="C:/tools/claude.cmd") as which,
            patch("subprocess.run", return_value=_completed(_claude_envelope_json())) as run,
        ):
            ClaudeCliRunner().run("p")
        which.assert_called_once_with("C:/tools/claude.cmd")
        assert run.call_args[0][0][0] == "C:/tools/claude.cmd"

    def test_missing_binary_is_non_transient_and_actionable(self):
        with patch("shutil.which", return_value=None), patch("subprocess.run") as run:
            with pytest.raises(ClaudeRunnerError) as ei:
                ClaudeCliRunner().run("p")
        run.assert_not_called()
        assert ei.value.transient is False
        assert "DECK_SUGGEST_CLAUDE_BIN" in str(ei.value)

    def test_oserror_on_start_is_non_transient(self):
        with (
            patch("shutil.which", return_value=FAKE_BIN),
            patch("subprocess.run", side_effect=PermissionError("denied")),
        ):
            with pytest.raises(ClaudeRunnerError) as ei:
                ClaudeCliRunner().run("p")
        assert ei.value.transient is False
        assert "denied" in str(ei.value)

    def test_nonzero_exit_is_transient_with_stderr(self):
        with (
            patch("shutil.which", return_value=FAKE_BIN),
            patch("subprocess.run", return_value=_completed(stderr="boom", returncode=1)),
        ):
            with pytest.raises(ClaudeRunnerError) as ei:
                ClaudeCliRunner().run("p")
        assert ei.value.transient is True
        assert "code 1" in str(ei.value)
        assert "boom" in str(ei.value)

    def test_nonzero_exit_without_output(self):
        with (
            patch("shutil.which", return_value=FAKE_BIN),
            patch("subprocess.run", return_value=_completed(returncode=2)),
        ):
            with pytest.raises(ClaudeRunnerError, match="no output"):
                ClaudeCliRunner().run("p")

    def test_large_stderr_truncated_to_500(self):
        stderr = "E" * 10_240
        with (
            patch("shutil.which", return_value=FAKE_BIN),
            patch("subprocess.run", return_value=_completed(stderr=stderr, returncode=1)),
        ):
            with pytest.raises(ClaudeRunnerError) as ei:
                ClaudeCliRunner().run("p")
        assert str(ei.value).count("E") == 500

    def test_non_json_stdout_is_transient(self):
        with (
            patch("shutil.which", return_value=FAKE_BIN),
            patch("subprocess.run", return_value=_completed("not json")),
        ):
            with pytest.raises(ClaudeRunnerError) as ei:
                ClaudeCliRunner().run("p")
        assert ei.value.transient is True
        assert "non-JSON" in str(ei.value)

    def test_envelope_not_a_dict_is_transient(self):
        with (
            patch("shutil.which", return_value=FAKE_BIN),
            patch("subprocess.run", return_value=_completed("[1, 2]")),
        ):
            with pytest.raises(ClaudeRunnerError) as ei:
                ClaudeCliRunner().run("p")
        assert ei.value.transient is True

    def test_is_error_envelope_is_transient(self):
        with (
            patch("shutil.which", return_value=FAKE_BIN),
            patch(
                "subprocess.run",
                return_value=_completed(_claude_envelope_json("overloaded", True)),
            ),
        ):
            with pytest.raises(ClaudeRunnerError) as ei:
                ClaudeCliRunner().run("p")
        assert ei.value.transient is True
        assert "overloaded" in str(ei.value)

    def test_envelope_without_result_is_transient(self):
        with (
            patch("shutil.which", return_value=FAKE_BIN),
            patch("subprocess.run", return_value=_completed(json.dumps({"is_error": False}))),
        ):
            with pytest.raises(ClaudeRunnerError, match="no text result") as ei:
                ClaudeCliRunner().run("p")
        assert ei.value.transient is True

    @pytest.mark.parametrize("raw", ["abc", "0", "-5"])
    def test_invalid_timeout_env_falls_back(self, monkeypatch, raw):
        monkeypatch.setenv("DECK_SUGGEST_TIMEOUT", raw)
        assert ClaudeCliRunner().timeout == DEFAULT_TIMEOUT

    def test_valid_timeout_env(self, monkeypatch):
        monkeypatch.setenv("DECK_SUGGEST_TIMEOUT", "42")
        assert ClaudeCliRunner().timeout == 42

    def test_prompt_never_logged(self):
        prompt = "SECRET-COLLECTION-DATA " * 10
        with (
            capture_logs() as logs,
            patch("shutil.which", return_value=FAKE_BIN),
            patch("subprocess.run", return_value=_completed(_claude_envelope_json("ok"))),
        ):
            ClaudeCliRunner().run(prompt)
        assert logs
        assert "SECRET-COLLECTION-DATA" not in repr(logs)
        assert any(entry.get("prompt_chars") == len(prompt) for entry in logs)


# ---------------------------------------------------------------------------
# API runner
# ---------------------------------------------------------------------------


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


class TestClaudeApiRunner:
    def test_happy_path_and_request_shape(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["request"] = request
            return httpx.Response(200, json=_claude_api_response_json())

        runner = ClaudeApiRunner(api_key=SENTINEL_KEY, client=_client(handler))
        assert runner.run("prompt text") == '{"deck_name": "X"}'

        req = captured["request"]
        assert str(req.url) == API_URL
        assert req.headers["x-api-key"] == SENTINEL_KEY
        assert req.headers["anthropic-version"] == ANTHROPIC_VERSION
        body = json.loads(req.content)
        assert body["model"] == DEFAULT_MODEL
        assert body["max_tokens"] == 8000
        assert body["messages"] == [{"role": "user", "content": "prompt text"}]

    def test_key_and_model_from_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", SENTINEL_KEY)
        monkeypatch.setenv("DECK_SUGGEST_MODEL", "claude-haiku-4-5")
        captured = {}

        def handler(request):
            captured["body"] = json.loads(request.content)
            captured["key"] = request.headers["x-api-key"]
            return httpx.Response(200, json=_claude_api_response_json())

        ClaudeApiRunner(client=_client(handler)).run("p")
        assert captured["body"]["model"] == "claude-haiku-4-5"
        assert captured["key"] == SENTINEL_KEY

    def test_multiple_text_blocks_concatenated_non_text_ignored(self):
        payload = _claude_api_response_json(
            {"type": "text", "text": '{"a": '},
            {"type": "thinking", "thinking": "hmm"},
            {"type": "text", "text": "1}"},
            "garbage",
        )
        runner = ClaudeApiRunner(
            api_key=SENTINEL_KEY, client=_client(lambda r: httpx.Response(200, json=payload))
        )
        assert runner.run("p") == '{"a": 1}'

    def test_missing_api_key_is_non_transient(self):
        with pytest.raises(ClaudeRunnerError) as ei:
            ClaudeApiRunner().run("p")
        assert ei.value.transient is False
        assert "ANTHROPIC_API_KEY not set" in str(ei.value)

    @pytest.mark.parametrize("status", [400, 401, 403, 404])
    def test_client_errors_non_transient(self, status):
        body = {"type": "error", "error": {"type": "x", "message": "bad thing"}}
        runner = ClaudeApiRunner(
            api_key=SENTINEL_KEY, client=_client(lambda r: httpx.Response(status, json=body))
        )
        with pytest.raises(ClaudeRunnerError) as ei:
            runner.run("p")
        assert ei.value.transient is False
        assert f"HTTP {status}" in str(ei.value)
        assert "bad thing" in str(ei.value)

    @pytest.mark.parametrize("status", [429, 500, 503, 529])
    def test_retryable_errors_transient(self, status):
        runner = ClaudeApiRunner(
            api_key=SENTINEL_KEY, client=_client(lambda r: httpx.Response(status, text="busy"))
        )
        with pytest.raises(ClaudeRunnerError) as ei:
            runner.run("p")
        assert ei.value.transient is True
        assert "busy" in str(ei.value)

    def test_error_body_empty(self):
        runner = ClaudeApiRunner(
            api_key=SENTINEL_KEY, client=_client(lambda r: httpx.Response(502, text=""))
        )
        with pytest.raises(ClaudeRunnerError, match="no details"):
            runner.run("p")

    def test_error_body_echoing_key_is_redacted(self):
        runner = ClaudeApiRunner(
            api_key=SENTINEL_KEY,
            client=_client(lambda r: httpx.Response(401, text=f"invalid key {SENTINEL_KEY}")),
        )
        with pytest.raises(ClaudeRunnerError) as ei:
            runner.run("p")
        assert SENTINEL_KEY not in str(ei.value)
        assert "***" in str(ei.value)

    def test_error_json_without_error_object(self):
        runner = ClaudeApiRunner(
            api_key=SENTINEL_KEY, client=_client(lambda r: httpx.Response(400, json=["x"]))
        )
        with pytest.raises(ClaudeRunnerError, match="HTTP 400"):
            runner.run("p")

    def test_timeout_is_transient(self):
        def handler(request):
            raise httpx.ReadTimeout("slow", request=request)

        runner = ClaudeApiRunner(api_key=SENTINEL_KEY, timeout=7, client=_client(handler))
        with pytest.raises(ClaudeRunnerError) as ei:
            runner.run("p")
        assert ei.value.transient is True
        assert "7s" in str(ei.value)

    def test_connect_error_is_transient(self):
        def handler(request):
            raise httpx.ConnectError("down", request=request)

        runner = ClaudeApiRunner(api_key=SENTINEL_KEY, client=_client(handler))
        with pytest.raises(ClaudeRunnerError) as ei:
            runner.run("p")
        assert ei.value.transient is True
        assert "ConnectError" in str(ei.value)

    def test_non_json_body_is_transient(self):
        runner = ClaudeApiRunner(
            api_key=SENTINEL_KEY, client=_client(lambda r: httpx.Response(200, text="<html>"))
        )
        with pytest.raises(ClaudeRunnerError, match="non-JSON") as ei:
            runner.run("p")
        assert ei.value.transient is True

    def test_missing_content_is_transient(self):
        runner = ClaudeApiRunner(
            api_key=SENTINEL_KEY, client=_client(lambda r: httpx.Response(200, json={"id": "x"}))
        )
        with pytest.raises(ClaudeRunnerError, match="no content"):
            runner.run("p")

    def test_default_client_used_when_none_injected(self):
        transport = httpx.MockTransport(
            lambda r: httpx.Response(200, json=_claude_api_response_json())
        )
        real_client = httpx.Client

        with patch(
            "src.deck_suggestions.claude_runner.httpx.Client",
            side_effect=lambda *a, **k: real_client(transport=transport),
        ):
            assert ClaudeApiRunner(api_key=SENTINEL_KEY).run("p") == '{"deck_name": "X"}'

    def test_repr_hides_key(self):
        assert SENTINEL_KEY not in repr(ClaudeApiRunner(api_key=SENTINEL_KEY))

    def test_sentinel_key_never_in_logs_or_errors(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", SENTINEL_KEY)
        responses = iter(
            [
                httpx.Response(200, json=_claude_api_response_json()),
                httpx.Response(401, json={"error": {"message": "invalid x-api-key"}}),
                httpx.Response(529, text="overloaded"),
            ]
        )
        runner = ClaudeApiRunner(client=_client(lambda r: next(responses)))
        errors = []
        with capture_logs() as logs:
            runner.run("p")
            for _ in range(2):
                with pytest.raises(ClaudeRunnerError) as ei:
                    runner.run("p")
                errors.append(ei.value)
        assert logs
        assert SENTINEL_KEY not in repr(logs)
        for exc in errors:
            assert SENTINEL_KEY not in str(exc)
            assert SENTINEL_KEY not in repr(exc)


# ---------------------------------------------------------------------------
# check() — fail-fast config validation used by the CLI (F172-T15)
# ---------------------------------------------------------------------------


class TestRunnerCheck:
    def test_cli_check_returns_resolved_path(self):
        with patch("shutil.which", return_value=FAKE_BIN) as which:
            assert ClaudeCliRunner(bin_path="claude").check() == FAKE_BIN
        which.assert_called_once_with("claude")

    def test_cli_check_missing_binary_is_non_transient(self):
        with patch("shutil.which", return_value=None):
            with pytest.raises(ClaudeRunnerError) as exc_info:
                ClaudeCliRunner(bin_path="nope-claude").check()
        assert exc_info.value.transient is False
        assert "nope-claude" in exc_info.value.message

    def test_cli_check_does_not_spawn_subprocess(self):
        with (
            patch("shutil.which", return_value=FAKE_BIN),
            patch("subprocess.run") as run,
        ):
            ClaudeCliRunner().check()
        run.assert_not_called()

    def test_api_check_with_key_passes(self):
        assert ClaudeApiRunner(api_key=SENTINEL_KEY).check() is None

    def test_api_check_missing_key_is_non_transient(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ClaudeRunnerError) as exc_info:
            ClaudeApiRunner().check()
        assert exc_info.value.transient is False
        assert "ANTHROPIC_API_KEY" in exc_info.value.message

    def test_api_check_empty_key_is_non_transient(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        with pytest.raises(ClaudeRunnerError):
            ClaudeApiRunner().check()


# ---------------------------------------------------------------------------
# get_runner
# ---------------------------------------------------------------------------


class TestGetRunner:
    def test_default_is_cli(self):
        runner = get_runner()
        assert isinstance(runner, ClaudeCliRunner)
        assert runner.provider == "cli"

    def test_env_selects_api(self, monkeypatch):
        monkeypatch.setenv("DECK_SUGGEST_PROVIDER", "API")
        runner = get_runner()
        assert isinstance(runner, ClaudeApiRunner)
        assert runner.provider == "api"
        assert runner.model == DEFAULT_MODEL

    def test_explicit_overrides_env(self, monkeypatch):
        monkeypatch.setenv("DECK_SUGGEST_PROVIDER", "api")
        assert isinstance(get_runner("cli"), ClaudeCliRunner)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="xyz"):
            get_runner("xyz")

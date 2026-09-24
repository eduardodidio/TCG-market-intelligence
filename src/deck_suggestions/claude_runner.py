"""Claude runners for deck suggestions (F172).

Two interchangeable backends, selected by ``DECK_SUGGEST_PROVIDER``:

- ``cli`` (default): the local ``claude`` CLI in print mode (``claude -p``).
- ``api``: the Anthropic Messages API over ``httpx`` (no SDK dependency).

Secrets (``ANTHROPIC_API_KEY``) come only from the environment and are never
logged or included in error messages. The prompt is never logged either — it
contains the user's collection — only its length.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Protocol

import httpx
import structlog

log = structlog.get_logger()

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_TIMEOUT = 300
DEFAULT_PROVIDER = "cli"
API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
API_MAX_TOKENS = 8000
MAX_ERROR_CHARS = 500

# `claude -p` in single-turn, JSON-envelope mode with every tool disabled
# (`--tools ""`): the model only answers, it never touches the filesystem.
_CLI_BASE_ARGS: tuple[str, ...] = (
    "-p",
    "--output-format",
    "json",
    "--max-turns",
    "1",
    "--tools",
    "",
)


class ClaudeRunnerError(Exception):
    """Raised when a Claude call fails. ``transient`` means a retry may succeed."""

    def __init__(self, message: str, transient: bool) -> None:
        super().__init__(message)
        self.message = message
        self.transient = transient


class ClaudeRunner(Protocol):
    provider: str
    model: str

    def run(self, prompt: str) -> str: ...


def _env_timeout() -> int:
    raw = os.environ.get("DECK_SUGGEST_TIMEOUT", str(DEFAULT_TIMEOUT))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        log.warning("deck_suggest.invalid_timeout", value=raw, default=DEFAULT_TIMEOUT)
        return DEFAULT_TIMEOUT
    if value <= 0:
        log.warning("deck_suggest.invalid_timeout", value=raw, default=DEFAULT_TIMEOUT)
        return DEFAULT_TIMEOUT
    return value


def _truncate(text: str | None) -> str:
    return (text or "").strip()[:MAX_ERROR_CHARS]


class ClaudeCliRunner:
    """Runs the prompt through the local ``claude`` CLI (``claude -p``)."""

    provider = "cli"

    def __init__(
        self,
        bin_path: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.bin_path = bin_path or os.environ.get("DECK_SUGGEST_CLAUDE_BIN", "claude")
        # Only pass --model when explicitly configured; otherwise the CLI's own default applies.
        self._model_override = model or os.environ.get("DECK_SUGGEST_MODEL") or None
        self.model = self._model_override or "default"
        self.timeout = timeout if timeout is not None else _env_timeout()

    def build_command(self, resolved_bin: str) -> list[str]:
        cmd = [resolved_bin, *_CLI_BASE_ARGS]
        if self._model_override:
            cmd += ["--model", self._model_override]
        return cmd

    def run(self, prompt: str) -> str:
        resolved = shutil.which(self.bin_path)
        if not resolved:
            raise ClaudeRunnerError(
                f"Claude CLI not found ('{self.bin_path}'). Install Claude Code and log in, "
                "or set DECK_SUGGEST_CLAUDE_BIN to the binary path "
                "(or use DECK_SUGGEST_PROVIDER=api with ANTHROPIC_API_KEY).",
                transient=False,
            )

        cmd = self.build_command(resolved)
        log.info(
            "deck_suggest.cli_run",
            model=self.model,
            prompt_chars=len(prompt),
            timeout=self.timeout,
        )
        workdir = tempfile.mkdtemp(prefix="deck_suggest_")
        try:
            try:
                proc = subprocess.run(
                    cmd,
                    input=prompt,
                    text=True,
                    encoding="utf-8",
                    capture_output=True,
                    timeout=self.timeout,
                    cwd=workdir,
                    shell=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise ClaudeRunnerError(
                    f"Claude CLI timed out after {self.timeout}s", transient=True
                ) from exc
            except OSError as exc:
                raise ClaudeRunnerError(
                    f"Failed to start Claude CLI: {_truncate(str(exc))}", transient=False
                ) from exc
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        if proc.returncode != 0:
            detail = _truncate(proc.stderr) or _truncate(proc.stdout) or "no output"
            log.warning("deck_suggest.cli_failed", returncode=proc.returncode)
            raise ClaudeRunnerError(
                f"Claude CLI exited with code {proc.returncode}: {detail}", transient=True
            )

        try:
            envelope = json.loads(proc.stdout or "")
        except json.JSONDecodeError as exc:
            raise ClaudeRunnerError(
                f"Claude CLI returned non-JSON output: {_truncate(proc.stdout)}",
                transient=True,
            ) from exc

        if not isinstance(envelope, dict):
            raise ClaudeRunnerError("Claude CLI returned an unexpected envelope", transient=True)
        if envelope.get("is_error"):
            detail = _truncate(str(envelope.get("result") or envelope.get("subtype") or ""))
            raise ClaudeRunnerError(f"Claude CLI reported an error: {detail}", transient=True)

        result = envelope.get("result")
        if not isinstance(result, str):
            raise ClaudeRunnerError("Claude CLI envelope has no text result", transient=True)

        log.info("deck_suggest.cli_done", result_chars=len(result))
        return result


class ClaudeApiRunner:
    """Calls the Anthropic Messages API directly via ``httpx`` (opt-in)."""

    provider = "api"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY") or None
        self.model = model or os.environ.get("DECK_SUGGEST_MODEL") or DEFAULT_MODEL
        self.timeout = timeout if timeout is not None else _env_timeout()
        self._client = client

    def __repr__(self) -> str:  # never expose the key
        return f"ClaudeApiRunner(model={self.model!r}, timeout={self.timeout})"

    def _post(self, headers: dict[str, str], body: dict) -> httpx.Response:
        if self._client is not None:
            return self._client.post(API_URL, headers=headers, json=body, timeout=self.timeout)
        with httpx.Client() as client:
            return client.post(API_URL, headers=headers, json=body, timeout=self.timeout)

    def run(self, prompt: str) -> str:
        if not self._api_key:
            raise ClaudeRunnerError(
                "ANTHROPIC_API_KEY not set. Add it to .env or use DECK_SUGGEST_PROVIDER=cli.",
                transient=False,
            )

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": API_MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        log.info(
            "deck_suggest.api_run",
            model=self.model,
            prompt_chars=len(prompt),
            timeout=self.timeout,
        )

        try:
            response = self._post(headers, body)
        except httpx.TimeoutException:
            raise ClaudeRunnerError(
                f"Anthropic API timed out after {self.timeout}s", transient=True
            ) from None
        except httpx.HTTPError as exc:
            # Exception text from httpx never includes headers, but keep only the type to be safe.
            raise ClaudeRunnerError(
                f"Anthropic API request failed: {type(exc).__name__}", transient=True
            ) from None

        status = response.status_code
        if status != 200:
            detail = self._error_detail(response)
            transient = status == 429 or status >= 500
            log.warning("deck_suggest.api_failed", status=status, transient=transient)
            raise ClaudeRunnerError(
                f"Anthropic API returned HTTP {status}: {detail}", transient=transient
            )

        try:
            data = response.json()
        except ValueError:
            raise ClaudeRunnerError(
                "Anthropic API returned non-JSON body", transient=True
            ) from None

        content = data.get("content") if isinstance(data, dict) else None
        if not isinstance(content, list):
            raise ClaudeRunnerError("Anthropic API response has no content", transient=True)

        text = "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
        log.info("deck_suggest.api_done", result_chars=len(text))
        return text

    def _error_detail(self, response: httpx.Response) -> str:
        try:
            data = response.json()
            message = data.get("error", {}).get("message") or response.text
        except (ValueError, AttributeError):
            message = response.text
        detail = _truncate(str(message))
        if self._api_key:
            detail = detail.replace(self._api_key, "***")
        return detail or "no details"


def get_runner(provider: str | None = None) -> ClaudeCliRunner | ClaudeApiRunner:
    """Return the runner for ``provider`` (default: ``$DECK_SUGGEST_PROVIDER`` or ``cli``)."""
    name = provider or os.environ.get("DECK_SUGGEST_PROVIDER") or DEFAULT_PROVIDER
    name = name.strip().lower()
    if name == "cli":
        return ClaudeCliRunner()
    if name == "api":
        return ClaudeApiRunner()
    raise ValueError(f"Unknown DECK_SUGGEST_PROVIDER '{name}' (expected 'cli' or 'api')")

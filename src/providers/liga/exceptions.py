"""Typed exception hierarchy for LigaMagic provider errors.

Mirrors the MYP exception pattern so callers (scan orchestrator,
sync orchestrator) can distinguish between transient failures
(rate-limit, server error) and permanent ones (404 not found).
"""

from __future__ import annotations


class LigaError(RuntimeError):
    """Base exception for all LigaMagic provider errors."""

    def __init__(
        self,
        message: str,
        *,
        url: str = "",
        status_code: int = 0,
        attempts: int = 1,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        self.attempts = attempts


class LigaNotFoundError(LigaError):
    """HTTP 404 — the requested card/resource does not exist on LigaMagic."""


class LigaRateLimitError(LigaError):
    """HTTP 429 — LigaMagic rate limit exceeded after retries."""


class LigaServerError(LigaError):
    """HTTP 5xx — LigaMagic server error after retries."""

"""Typed exception hierarchy for MYP HTTP errors.

Provides fine-grained exception types so callers (scan orchestrator,
sync orchestrator) can distinguish between transient failures
(rate-limit, server error) and permanent ones (404 not found).
"""

from __future__ import annotations


class MypError(RuntimeError):
    """Base exception for all MYP provider errors."""

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


class NotFoundError(MypError):
    """HTTP 404 — the requested resource does not exist on MYP."""


class RateLimitError(MypError):
    """HTTP 429 — MYP rate limit exceeded after retries."""


class ServerError(MypError):
    """HTTP 5xx — MYP server error after retries."""

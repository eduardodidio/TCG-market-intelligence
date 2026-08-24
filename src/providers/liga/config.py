"""Configuration for the LigaMagic provider."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LigaConfig:
    """Tuning knobs for the LigaMagic browser-based provider."""

    delay_seconds: float = 4.0
    timeout_seconds: float = 30.0
    headless: bool = True
    max_retries: int = 2

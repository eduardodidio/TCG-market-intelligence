"""Shared currency types for import/conversion (F171)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SupportedCurrency = Literal["BRL", "USD"]
CurrencyChoice = Literal["auto", "BRL", "USD"]
# How the currency was decided (most -> least authoritative)
CurrencySource = Literal[
    "user", "column", "header", "symbol", "number_format", "origin", "default"
]


@dataclass(frozen=True)
class CurrencyDetection:
    currency: SupportedCurrency
    source: CurrencySource
    confidence: Literal["high", "medium", "low"]
    evidence: list[str] = field(default_factory=list)  # human-readable reasons
    unsupported_symbols: list[str] = field(default_factory=list)  # e.g. ["€"]

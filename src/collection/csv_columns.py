"""Pure header-alias resolution and file-level currency detection (F171).

Maps arbitrary CSV headers (Liga Magic, ManaBox, or a generic spreadsheet) to
canonical collection fields, and decides which currency a file's price
column is in without ever guessing a USD file into BRL storage.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from src.currency.money import detect_symbol, number_format_hint
from src.currency.types import CurrencyChoice, CurrencyDetection, SupportedCurrency

_MAX_SAMPLE = 200

# canonical field -> accepted headers (Liga header first where one exists).
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "set_code": ("Edicao (Sigla)", "Set code", "Set", "Edition code", "Sigla"),
    "collector_number": ("Card #", "Collector number", "Number", "Numero"),
    "name_en": ("Card (EN)", "Name", "Card name", "Card"),
    "name_pt": ("Card (PT)", "Nome"),
    "set_name_en": ("Edicao (EN)", "Set name"),
    "set_name_pt": ("Edicao (PTBR)",),
    "quantity": ("Quantidade", "Quantity", "Qty", "Count", "Qtd"),
    "quality": ("Qualidade (M NM SP MP HP D)", "Condition", "Qualidade"),
    "language": ("Idioma (BR EN DE ES FR IT JP KO RU TW)", "Language", "Idioma"),
    "rarity": ("Raridade (M R U C)", "Rarity"),
    "color": ("Cor (W U B R G M A L)",),
    "extras": ("Extras", "Foil"),
    "notes": ("Comentario", "Notes", "Comment"),
    "price": (
        "Price",
        "Purchase price",
        "Preço",
        "Preco",
        "Valor",
        "Preço pago",
        "Preco (R$)",
        "Price (USD)",
        "Price (BRL)",
    ),
    "currency": ("Currency", "Moeda", "Purchase price currency"),
}

_PRICE_PREFIXES = ("purchase price", "price", "preco", "valor")
_PRICE_PREFIX_ALLOWED_SUFFIXES = {"pago"}

_HEADER_CURRENCY_RE = re.compile(r"[\(\[]\s*([^)\]]+?)\s*[\)\]]")
_SYMBOL_LABEL = {"BRL": "R$", "USD": "US$"}


@dataclass
class ColumnMap:
    fields: dict[str, str]
    origin: Literal["liga", "manabox", "generic"]
    header_currency: SupportedCurrency | None = None


def _normalize(s: str) -> str:
    s = s.lstrip("﻿")
    folded = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    folded = re.sub(r"\s+", " ", folded)
    return folded.strip().lower()


def _looks_like_price_header(normalized: str) -> bool:
    for prefix in _PRICE_PREFIXES:
        if normalized.startswith(prefix):
            rest = normalized[len(prefix) :].strip()
            if not rest or rest[0] in "([" or rest in _PRICE_PREFIX_ALLOWED_SUFFIXES:
                return True
    return False


def _header_currency(header: str) -> SupportedCurrency | None:
    match = _HEADER_CURRENCY_RE.search(header)
    if not match:
        return None
    token = _normalize(match.group(1))
    if token in ("r$", "brl"):
        return "BRL"
    if token in ("us$", "usd"):
        return "USD"
    return None


def _detect_origin(normalized_map: dict[str, str]) -> Literal["liga", "manabox", "generic"]:
    if _normalize("Edicao (Sigla)") in normalized_map and _normalize("Card #") in normalized_map:
        return "liga"
    has_set_code = _normalize("Set code") in normalized_map
    has_collector_number = _normalize("Collector number") in normalized_map
    if _normalize("Purchase price currency") in normalized_map or (
        has_set_code and has_collector_number
    ):
        return "manabox"
    return "generic"


def resolve_columns(headers: list[str]) -> ColumnMap:
    """Map raw CSV headers to canonical fields, detect origin and header currency."""
    if not headers:
        return ColumnMap(fields={}, origin="generic", header_currency=None)

    normalized_map: dict[str, str] = {}
    for raw in headers:
        norm = _normalize(raw)
        if norm and norm not in normalized_map:
            normalized_map[norm] = raw.lstrip("﻿")

    fields: dict[str, str] = {}

    for canonical, aliases in FIELD_ALIASES.items():
        if canonical in ("price", "currency"):
            continue
        for alias in aliases:
            header = normalized_map.get(_normalize(alias))
            if header is not None:
                fields[canonical] = header
                break

    currency_header: str | None = None
    for alias in FIELD_ALIASES["currency"]:
        header = normalized_map.get(_normalize(alias))
        if header is not None:
            currency_header = header
            fields["currency"] = header
            break

    price_header: str | None = None
    for alias in FIELD_ALIASES["price"]:
        header = normalized_map.get(_normalize(alias))
        if header is not None and header != currency_header:
            price_header = header
            break
    if price_header is None:
        for norm, header in normalized_map.items():
            if header == currency_header:
                continue
            if _looks_like_price_header(norm):
                price_header = header
                break
    if price_header is not None:
        fields["price"] = price_header

    header_currency = _header_currency(price_header) if price_header else None
    origin = _detect_origin(normalized_map)

    return ColumnMap(fields=fields, origin=origin, header_currency=header_currency)


def _sample_price_cells(price_header: str | None, rows: list[dict[str, str]]) -> list[str]:
    if not price_header:
        return []
    sample: list[str] = []
    for row in rows:
        cell = (row.get(price_header) or "").strip()
        if not cell:
            continue
        sample.append(cell)
        if len(sample) >= _MAX_SAMPLE:
            break
    return sample


def detect_file_currency(
    cmap: ColumnMap,
    rows: list[dict[str, str]],
    choice: CurrencyChoice = "auto",
) -> CurrencyDetection:
    """Decide the currency of a CSV's price column, most authoritative source first."""
    if choice in ("BRL", "USD"):
        return CurrencyDetection(
            currency=choice,
            source="user",
            confidence="high",
            evidence=[f"user override: {choice}"],
        )

    unsupported: list[str] = []
    currency_header = cmap.fields.get("currency")
    price_header = cmap.fields.get("price")

    if currency_header:
        counts = {"BRL": 0, "USD": 0}
        checked = 0
        for row in rows:
            cell = (row.get(currency_header) or "").strip()
            if not cell:
                continue
            checked += 1
            if checked > _MAX_SAMPLE:
                break
            sym = detect_symbol(cell)
            if sym == "BRL":
                counts["BRL"] += 1
            elif sym == "USD":
                counts["USD"] += 1
            elif sym is not None and sym not in unsupported:
                unsupported.append(sym)

        total_valid = counts["BRL"] + counts["USD"]
        if total_valid > 0:
            majority: SupportedCurrency = "BRL" if counts["BRL"] >= counts["USD"] else "USD"
            confidence: Literal["high", "medium", "low"] = (
                "high" if counts["BRL"] == 0 or counts["USD"] == 0 else "medium"
            )
            return CurrencyDetection(
                currency=majority,
                source="column",
                confidence=confidence,
                evidence=[f"column: {counts[majority]} {majority}"],
                unsupported_symbols=unsupported,
            )

    if cmap.header_currency:
        return CurrencyDetection(
            currency=cmap.header_currency,
            source="header",
            confidence="high",
            evidence=[f"header: {price_header} -> {cmap.header_currency}"],
            unsupported_symbols=unsupported,
        )

    sample_cells = _sample_price_cells(price_header, rows)

    if sample_cells:
        symbol_counts = {"BRL": 0, "USD": 0}
        for cell in sample_cells:
            sym = detect_symbol(cell)
            if sym == "BRL":
                symbol_counts["BRL"] += 1
            elif sym == "USD":
                symbol_counts["USD"] += 1
            elif sym == "EUR" and "EUR" not in unsupported:
                unsupported.append("EUR")

        total_symbols = symbol_counts["BRL"] + symbol_counts["USD"]
        if total_symbols > 0:
            majority = "BRL" if symbol_counts["BRL"] >= symbol_counts["USD"] else "USD"
            mixed = symbol_counts["BRL"] > 0 and symbol_counts["USD"] > 0
            evidence = [f"symbol: {symbol_counts[majority]} {_SYMBOL_LABEL[majority]}"]
            if mixed:
                other: SupportedCurrency = "USD" if majority == "BRL" else "BRL"
                evidence.append(f"symbol: {symbol_counts[other]} {_SYMBOL_LABEL[other]}")
                evidence.append("mixed symbols")
            return CurrencyDetection(
                currency=majority,
                source="symbol",
                confidence="low" if mixed else "medium",
                evidence=evidence,
                unsupported_symbols=unsupported,
            )

        fmt_counts = {"BRL": 0, "USD": 0}
        for cell in sample_cells:
            hint = number_format_hint(cell)
            if hint:
                fmt_counts[hint] += 1

        total_fmt = fmt_counts["BRL"] + fmt_counts["USD"]
        if total_fmt > 0:
            majority = "BRL" if fmt_counts["BRL"] >= fmt_counts["USD"] else "USD"
            return CurrencyDetection(
                currency=majority,
                source="number_format",
                confidence="low",
                evidence=[f"number_format: {fmt_counts[majority]} {majority}"],
                unsupported_symbols=unsupported,
            )

    if cmap.origin == "liga":
        return CurrencyDetection(
            currency="BRL",
            source="origin",
            confidence="medium",
            evidence=["origin: liga"],
            unsupported_symbols=unsupported,
        )

    return CurrencyDetection(
        currency="BRL",
        source="default",
        confidence="low",
        evidence=["default: BRL"],
        unsupported_symbols=unsupported,
    )

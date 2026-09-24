"""Tests for csv_columns.py: header aliases and file-level currency detection (F171-T04)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.collection.csv_columns import (
    ColumnMap,
    _header_currency,
    _looks_like_price_header,
    detect_file_currency,
    resolve_columns,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "collection_import"

LIGA_HEADERS = [
    "Edicao (PTBR)",
    "Edicao (EN)",
    "Edicao (Sigla)",
    "Card (PT)",
    "Card (EN)",
    "Quantidade",
    "Qualidade (M NM SP MP HP D)",
    "Idioma (BR EN DE ES FR IT JP KO RU TW)",
    "Raridade (M R U C)",
    "Cor (W U B R G M A L)",
    "Extras",
    "Card #",
    "Comentario",
]


def _read_csv(name: str, encoding: str = "utf-8") -> tuple[list[str], list[dict[str, str]]]:
    with open(FIXTURES / name, encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames or []
    return list(headers), rows


# --- resolve_columns -------------------------------------------------------


def test_all_13_liga_headers_resolve_and_origin_is_liga():
    cmap = resolve_columns(LIGA_HEADERS)
    assert cmap.origin == "liga"
    expected_fields = {
        "set_name_pt",
        "set_name_en",
        "set_code",
        "name_pt",
        "name_en",
        "quantity",
        "quality",
        "language",
        "rarity",
        "color",
        "extras",
        "collector_number",
        "notes",
    }
    assert set(cmap.fields) == expected_fields
    assert cmap.fields["set_code"] == "Edicao (Sigla)"
    assert cmap.fields["collector_number"] == "Card #"


def test_liga_brl_no_price_fixture_origin_liga_no_price_field():
    headers, _ = _read_csv("liga_brl_no_price.csv", encoding="cp1252")
    cmap = resolve_columns(headers)
    assert cmap.origin == "liga"
    assert "price" not in cmap.fields


def test_manabox_fixtures_origin_manabox():
    for name in ("manabox_usd.csv", "manabox_brl.csv"):
        headers, _ = _read_csv(name)
        cmap = resolve_columns(headers)
        assert cmap.origin == "manabox", name
        assert cmap.fields["price"] == "Purchase price"
        assert cmap.fields["currency"] == "Purchase price currency"


def test_generic_fixtures_have_price_field():
    # Note: these fixtures also carry "Set code"/"Collector number" headers,
    # which the origin heuristic (brief 03-csv-import.md) classifies as "manabox".
    for name in ("generic_brl_symbol.csv", "generic_usd_symbol.csv", "ambiguous_no_hint.csv"):
        headers, _ = _read_csv(name)
        cmap = resolve_columns(headers)
        assert cmap.fields["price"] == "Price"


def test_liga_brl_no_price_only_origin_generic_variant():
    cmap = resolve_columns(["Name", "Notes"])
    assert cmap.origin == "generic"


def test_liga_brl_with_price_resolves_price_and_header_currency():
    headers, _ = _read_csv("liga_brl_with_price.csv")
    cmap = resolve_columns(headers)
    assert cmap.fields["price"] == "Preco (R$)"
    assert cmap.header_currency == "BRL"


def test_price_header_detection_excludes_unrelated_headers():
    cmap = resolve_columns(["Name", "Price source", "Quantity"])
    assert "price" not in cmap.fields


def test_price_header_prefix_heuristic_matches_price_variants():
    for header in ("Preço pago", "Price (USD)", "Purchase price"):
        cmap = resolve_columns(["Name", header])
        assert cmap.fields.get("price") == header, header


def test_price_header_excludes_currency_column():
    cmap = resolve_columns(["Name", "Purchase price currency"])
    assert "price" not in cmap.fields
    assert cmap.fields["currency"] == "Purchase price currency"


def test_bom_on_first_header():
    cmap = resolve_columns(["﻿Edicao (Sigla)", "Card #"])
    assert cmap.origin == "liga"
    assert cmap.fields["set_code"] == "Edicao (Sigla)"


def test_extra_spaces_in_header():
    cmap = resolve_columns(["Edicao  (Sigla)", "Card  #"])
    assert cmap.origin == "liga"


def test_uppercase_preco_header():
    cmap = resolve_columns(["Name", "PREÇO"])
    assert cmap.fields["price"] == "PREÇO"


def test_empty_header_list_no_exception():
    cmap = resolve_columns([])
    assert cmap == ColumnMap(fields={}, origin="generic")
    assert cmap.header_currency is None


# --- detect_file_currency ---------------------------------------------------


@pytest.mark.parametrize(
    "fixture,encoding,expected_currency,expected_source",
    [
        ("liga_brl_no_price.csv", "cp1252", "BRL", "origin"),
        ("liga_brl_with_price.csv", "utf-8", "BRL", "header"),
        ("generic_brl_symbol.csv", "utf-8", "BRL", "symbol"),
        ("generic_usd_symbol.csv", "utf-8", "USD", "symbol"),
        ("manabox_usd.csv", "utf-8", "USD", "column"),
        ("manabox_brl.csv", "utf-8", "BRL", "column"),
        ("ambiguous_no_hint.csv", "utf-8", "BRL", "default"),
    ],
)
def test_detect_file_currency_per_fixture(fixture, encoding, expected_currency, expected_source):
    headers, rows = _read_csv(fixture, encoding=encoding)
    cmap = resolve_columns(headers)
    detection = detect_file_currency(cmap, rows)
    assert detection.currency == expected_currency
    assert detection.source == expected_source


def test_ambiguous_no_hint_confidence_low():
    headers, rows = _read_csv("ambiguous_no_hint.csv")
    cmap = resolve_columns(headers)
    detection = detect_file_currency(cmap, rows)
    assert detection.confidence == "low"


def test_manabox_brl_detects_column_despite_dot_decimals():
    headers, rows = _read_csv("manabox_brl.csv")
    cmap = resolve_columns(headers)
    detection = detect_file_currency(cmap, rows)
    assert detection.currency == "BRL"
    assert detection.source == "column"
    assert any("BRL" in e for e in detection.evidence)


def test_user_choice_overrides_everything():
    headers, rows = _read_csv("liga_brl_with_price.csv")
    cmap = resolve_columns(headers)
    detection = detect_file_currency(cmap, rows, choice="USD")
    assert detection.currency == "USD"
    assert detection.source == "user"
    assert detection.confidence == "high"


def test_mixed_symbols_majority_brl_low_confidence():
    headers = ["Name", "Price"]
    rows = [
        {"Name": "A", "Price": "R$ 10,00"},
        {"Name": "B", "Price": "R$ 5,00"},
        {"Name": "C", "Price": "R$ 2,50"},
        {"Name": "D", "Price": "US$ 3.10"},
    ]
    cmap = resolve_columns(headers)
    detection = detect_file_currency(cmap, rows)
    assert detection.currency == "BRL"
    assert detection.source == "symbol"
    assert detection.confidence == "low"
    assert any("mixed" in e for e in detection.evidence)


def test_currency_column_with_only_eur_falls_through():
    headers = ["Name", "Price", "Currency"]
    rows = [
        {"Name": "A", "Price": "10", "Currency": "EUR"},
        {"Name": "B", "Price": "3", "Currency": "EUR"},
    ]
    cmap = resolve_columns(headers)
    detection = detect_file_currency(cmap, rows)
    assert "EUR" in detection.unsupported_symbols
    assert detection.source in ("default", "origin")
    assert detection.currency == "BRL"


def test_price_column_all_empty_falls_through_to_default():
    headers = ["Name", "Price"]
    rows = [{"Name": "A", "Price": ""}, {"Name": "B", "Price": ""}]
    cmap = resolve_columns(headers)
    detection = detect_file_currency(cmap, rows)
    assert detection.source == "default"
    assert detection.currency == "BRL"


def test_only_200_price_cells_sampled():
    headers = ["Name", "Price"]
    rows = [{"Name": f"Card {i}", "Price": "R$ 1,00"} for i in range(200)]
    rows += [{"Name": f"Card {i}", "Price": "US$ 1.00"} for i in range(50)]
    cmap = resolve_columns(headers)
    detection = detect_file_currency(cmap, rows)
    assert detection.currency == "BRL"
    assert detection.evidence == ["symbol: 200 R$"]


# --- helper functions --------------------------------------------------


def test_looks_like_price_header_exact_prefix_match():
    assert _looks_like_price_header("valor") is True
    assert _looks_like_price_header("preco") is True


def test_looks_like_price_header_rejects_unrelated_suffix():
    assert _looks_like_price_header("price source") is False


def test_looks_like_price_header_allows_pago_suffix():
    assert _looks_like_price_header("valor pago") is True


def test_valor_pago_header_not_in_alias_list_matches_via_heuristic():
    cmap = resolve_columns(["Name", "Valor pago"])
    assert cmap.fields["price"] == "Valor pago"


def test_header_currency_unrecognized_token_returns_none():
    assert _header_currency("Price (EUR)") is None


def test_price_header_heuristic_matches_currency_parenthetical_not_in_alias_list():
    cmap = resolve_columns(["Name", "Price (EUR)"])
    assert cmap.fields["price"] == "Price (EUR)"
    assert cmap.header_currency is None


def test_currency_column_skips_empty_cells_and_caps_at_200():
    headers = ["Name", "Price", "Currency"]
    rows = [{"Name": "empty", "Price": "10", "Currency": ""}]
    rows += [{"Name": f"row{i}", "Price": "10", "Currency": "BRL"} for i in range(250)]
    cmap = resolve_columns(headers)
    detection = detect_file_currency(cmap, rows)
    assert detection.source == "column"
    assert detection.evidence == ["column: 200 BRL"]


def test_eur_symbol_only_falls_through_to_number_format():
    headers = ["Name", "Price"]
    rows = [{"Name": "A", "Price": "€ 3,00"}, {"Name": "B", "Price": "12,50"}]
    cmap = resolve_columns(headers)
    detection = detect_file_currency(cmap, rows)
    assert "EUR" in detection.unsupported_symbols
    assert detection.source == "number_format"
    assert detection.currency == "BRL"


def test_number_format_hint_majority_usd():
    headers = ["Name", "Price"]
    rows = [{"Name": "A", "Price": "12.50"}, {"Name": "B", "Price": "3.00"}]
    cmap = resolve_columns(headers)
    detection = detect_file_currency(cmap, rows)
    assert detection.source == "number_format"
    assert detection.currency == "USD"

"""Tests for MYP search response parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.domain.models import MypSearchResult
from src.parsers.myp import parse_search_results

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load_json(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Valid responses
# ---------------------------------------------------------------------------


class TestParseSearchResultsValid:
    """Scenario 1: parse valid search JSON response."""

    def test_multiple_results(self):
        raw = _load_json("myp_search_bolt.json")
        results = parse_search_results(raw)

        assert len(results) == 3
        assert all(isinstance(r, MypSearchResult) for r in results)

    def test_first_result_fields(self):
        raw = _load_json("myp_search_bolt.json")
        results = parse_search_results(raw)
        first = results[0]

        assert first.external_id == "45231"
        assert first.name == "Raio / Lightning Bolt"
        assert first.slug == "raio-lightning-bolt"
        assert first.url == "https://mypcards.com/magic/produto/45231/raio-lightning-bolt"
        assert first.sku == "magic_sta_062"
        assert first.set_code == "sta"
        assert first.collector_number == "062"
        assert first.image_url == "https://mypcards.com/images/magic/sta/062.jpg"

    def test_single_result(self):
        raw = _load_json("myp_search_single.json")
        results = parse_search_results(raw)

        assert len(results) == 1
        result = results[0]
        assert result.external_id == "179334"
        assert result.name == "O Um Anel / The One Ring"
        assert result.slug == "o-um-anel-the-one-ring"
        assert result.sku == "magic_ltr_246"
        assert result.set_code == "ltr"
        assert result.collector_number == "246"

    def test_url_construction(self):
        raw = _load_json("myp_search_single.json")
        results = parse_search_results(raw)
        assert results[0].url == "https://mypcards.com/magic/produto/179334/o-um-anel-the-one-ring"

    def test_all_results_have_set_code(self):
        raw = _load_json("myp_search_bolt.json")
        results = parse_search_results(raw)
        set_codes = [r.set_code for r in results]
        assert set_codes == ["sta", "m11", "a25"]


# ---------------------------------------------------------------------------
# Empty responses
# ---------------------------------------------------------------------------


class TestParseSearchResultsEmpty:
    """Scenario 2: parse empty results array."""

    def test_empty_array(self):
        raw = _load_json("myp_search_empty.json")
        results = parse_search_results(raw)
        assert results == []

    def test_empty_string(self):
        results = parse_search_results("")
        assert results == []


# ---------------------------------------------------------------------------
# Malformed input
# ---------------------------------------------------------------------------


class TestParseSearchResultsMalformed:
    """Scenario 3: parse malformed JSON (graceful fallback)."""

    def test_invalid_json(self):
        results = parse_search_results("{not valid json")
        assert results == []

    def test_html_response(self):
        results = parse_search_results("<html><body>Error</body></html>")
        assert results == []

    def test_none_input(self):
        results = parse_search_results(None)  # type: ignore[arg-type]
        assert results == []

    def test_json_object_instead_of_array(self):
        results = parse_search_results('{"error": "rate limited"}')
        assert results == []

    def test_json_string_instead_of_array(self):
        results = parse_search_results('"just a string"')
        assert results == []

    def test_array_of_non_dicts(self):
        results = parse_search_results("[1, 2, 3]")
        assert results == []

    def test_array_with_mixed_types(self):
        raw = json.dumps(
            [
                {"id": 100, "nome": "Valid Card", "slug": "valid-card"},
                "not a dict",
                42,
            ]
        )
        results = parse_search_results(raw)
        assert len(results) == 1
        assert results[0].external_id == "100"


# ---------------------------------------------------------------------------
# Missing fields
# ---------------------------------------------------------------------------


class TestParseSearchResultsMissingFields:
    """Scenario 4: parse response with missing optional fields."""

    def test_missing_sku(self):
        raw = json.dumps([{"id": 100, "nome": "Test Card", "slug": "test-card"}])
        results = parse_search_results(raw)
        assert len(results) == 1
        assert results[0].sku is None
        assert results[0].set_code is None
        assert results[0].collector_number is None

    def test_missing_image(self):
        raw = json.dumps(
            [{"id": 100, "nome": "Test Card", "slug": "test-card", "sku": "magic_dmr_001"}]
        )
        results = parse_search_results(raw)
        assert results[0].image_url is None

    def test_missing_nome_falls_back_to_slug(self):
        raw = json.dumps([{"id": 100, "slug": "test-card"}])
        results = parse_search_results(raw)
        assert len(results) == 1
        assert results[0].name == "test-card"

    def test_missing_id_skips_item(self):
        raw = json.dumps([{"nome": "No ID Card", "slug": "no-id-card"}])
        results = parse_search_results(raw)
        assert results == []

    def test_missing_slug_skips_item(self):
        raw = json.dumps([{"id": 100, "nome": "No Slug Card"}])
        results = parse_search_results(raw)
        assert results == []

    def test_empty_slug_skips_item(self):
        raw = json.dumps([{"id": 100, "nome": "Empty Slug Card", "slug": ""}])
        results = parse_search_results(raw)
        assert results == []

    def test_empty_sku_treated_as_none(self):
        raw = json.dumps([{"id": 100, "nome": "Empty SKU", "slug": "empty-sku", "sku": ""}])
        results = parse_search_results(raw)
        assert results[0].sku is None
        assert results[0].set_code is None

    @pytest.mark.parametrize("invalid_sku", ["invalid", "magic", "magic_only"])
    def test_invalid_sku_yields_no_set_code(self, invalid_sku):
        raw = json.dumps([{"id": 100, "nome": "Bad SKU", "slug": "bad-sku", "sku": invalid_sku}])
        results = parse_search_results(raw)
        assert len(results) == 1
        assert results[0].sku == invalid_sku
        assert results[0].set_code is None

    def test_id_coerced_to_string(self):
        """Numeric id from JSON is stored as str."""
        raw = json.dumps([{"id": 99999, "nome": "Numeric ID", "slug": "numeric-id"}])
        results = parse_search_results(raw)
        assert results[0].external_id == "99999"
        assert isinstance(results[0].external_id, str)

"""Unit tests for src.catalog.scryfall module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.catalog.scryfall import (
    RARITY_MAP,
    CatalogCard,
    _cleanup_old_files,
    _get_download_url,
    _parse_card,
    download_bulk_data,
    parse_bulk_cards,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CARDS_RAW = [
    {
        "name": "Lightning Bolt",
        "set": "lea",
        "collector_number": "161",
        "rarity": "common",
        "color_identity": ["R"],
        "mana_cost": "{R}",
        "type_line": "Instant",
        "image_uris": {"normal": "https://img.scryfall.com/bolt.jpg"},
        "lang": "en",
        "games": ["paper", "mtgo"],
    },
    {
        "name": "Counterspell",
        "set": "lea",
        "collector_number": "54",
        "rarity": "uncommon",
        "color_identity": ["U"],
        "mana_cost": "{U}{U}",
        "type_line": "Instant",
        "image_uris": {"normal": "https://img.scryfall.com/counter.jpg"},
        "lang": "en",
        "games": ["paper"],
    },
    {
        "name": "Black Lotus",
        "set": "lea",
        "collector_number": "232",
        "rarity": "rare",
        "color_identity": [],
        "mana_cost": "{0}",
        "type_line": "Artifact",
        "image_uris": {"normal": "https://img.scryfall.com/lotus.jpg"},
        "lang": "en",
        "games": ["paper", "mtgo"],
    },
    {
        # Digital-only card — should be filtered out
        "name": "Arena Exclusive",
        "set": "anb",
        "collector_number": "1",
        "rarity": "common",
        "color_identity": ["W"],
        "mana_cost": "{W}",
        "type_line": "Creature",
        "image_uris": {"normal": "https://img.scryfall.com/arena.jpg"},
        "lang": "en",
        "games": ["arena"],
    },
    {
        # Non-English card — should be filtered out
        "name": "Raio",
        "set": "lea",
        "collector_number": "161",
        "rarity": "common",
        "color_identity": ["R"],
        "mana_cost": "{R}",
        "type_line": "Mágica Instantânea",
        "image_uris": {"normal": "https://img.scryfall.com/raio.jpg"},
        "lang": "pt",
        "games": ["paper"],
    },
]

BULK_API_RESPONSE = {
    "object": "list",
    "has_more": False,
    "data": [
        {
            "object": "bulk_data",
            "type": "oracle_cards",
            "download_uri": "https://example.com/oracle.json",
            "size": 50_000_000,
        },
        {
            "object": "bulk_data",
            "type": "default_cards",
            "download_uri": "https://example.com/default-cards.json",
            "size": 150_000_000,
        },
        {
            "object": "bulk_data",
            "type": "all_cards",
            "download_uri": "https://example.com/all-cards.json",
            "size": 1_500_000_000,
        },
    ],
}


@pytest.fixture
def sample_json_file(tmp_path: Path) -> Path:
    """Create a temporary JSON file with sample card data."""
    file = tmp_path / "test-cards.json"
    file.write_text(json.dumps(SAMPLE_CARDS_RAW), encoding="utf-8")
    return file


# ---------------------------------------------------------------------------
# CatalogCard dataclass
# ---------------------------------------------------------------------------


class TestCatalogCard:
    def test_create_with_all_fields(self):
        card = CatalogCard(
            name_en="Lightning Bolt",
            set_code="lea",
            collector_number="161",
            rarity="C",
            color_identity="R",
            mana_cost="{R}",
            type_line="Instant",
            image_uri="https://img.scryfall.com/bolt.jpg",
            name_pt="Raio",
        )
        assert card.name_en == "Lightning Bolt"
        assert card.set_code == "lea"
        assert card.collector_number == "161"
        assert card.rarity == "C"
        assert card.color_identity == "R"
        assert card.mana_cost == "{R}"
        assert card.type_line == "Instant"
        assert card.image_uri == "https://img.scryfall.com/bolt.jpg"
        assert card.name_pt == "Raio"

    def test_name_pt_defaults_to_none(self):
        card = CatalogCard(
            name_en="Bolt",
            set_code="lea",
            collector_number="1",
            rarity="C",
            color_identity="R",
            mana_cost="{R}",
            type_line="Instant",
            image_uri=None,
        )
        assert card.name_pt is None

    def test_image_uri_can_be_none(self):
        card = CatalogCard(
            name_en="Token",
            set_code="t2x",
            collector_number="T1",
            rarity="S",
            color_identity="",
            mana_cost="",
            type_line="Token",
            image_uri=None,
        )
        assert card.image_uri is None

    def test_frozen(self):
        card = CatalogCard(
            name_en="X",
            set_code="x",
            collector_number="1",
            rarity="C",
            color_identity="",
            mana_cost="",
            type_line="",
            image_uri=None,
        )
        with pytest.raises(AttributeError):
            card.name_en = "Y"  # type: ignore[misc]

    def test_equality(self):
        kwargs = dict(
            name_en="A",
            set_code="a",
            collector_number="1",
            rarity="C",
            color_identity="",
            mana_cost="",
            type_line="",
            image_uri=None,
        )
        assert CatalogCard(**kwargs) == CatalogCard(**kwargs)


# ---------------------------------------------------------------------------
# _parse_card
# ---------------------------------------------------------------------------


class TestParseCard:
    def test_parses_paper_english_card(self):
        card = _parse_card(SAMPLE_CARDS_RAW[0])
        assert card is not None
        assert card.name_en == "Lightning Bolt"
        assert card.set_code == "lea"
        assert card.collector_number == "161"
        assert card.rarity == "C"
        assert card.color_identity == "R"
        assert card.mana_cost == "{R}"
        assert card.type_line == "Instant"
        assert card.image_uri == "https://img.scryfall.com/bolt.jpg"
        assert card.name_pt is None

    def test_filters_arena_only(self):
        assert _parse_card(SAMPLE_CARDS_RAW[3]) is None

    def test_filters_non_english(self):
        assert _parse_card(SAMPLE_CARDS_RAW[4]) is None

    def test_multi_color_identity(self):
        raw = {**SAMPLE_CARDS_RAW[0], "color_identity": ["W", "U", "B"]}
        card = _parse_card(raw)
        assert card is not None
        assert card.color_identity == "WUB"

    def test_empty_color_identity(self):
        card = _parse_card(SAMPLE_CARDS_RAW[2])
        assert card is not None
        assert card.color_identity == ""

    def test_no_image_uris(self):
        raw = {**SAMPLE_CARDS_RAW[0]}
        del raw["image_uris"]
        card = _parse_card(raw)
        assert card is not None
        assert card.image_uri is None

    def test_rarity_mapping(self):
        for raw_rarity, expected in RARITY_MAP.items():
            raw = {**SAMPLE_CARDS_RAW[0], "rarity": raw_rarity}
            card = _parse_card(raw)
            assert card is not None
            assert card.rarity == expected, f"{raw_rarity} -> {expected}"

    def test_unknown_rarity_uses_first_char(self):
        raw = {**SAMPLE_CARDS_RAW[0], "rarity": "timeshifted"}
        card = _parse_card(raw)
        assert card is not None
        assert card.rarity == "T"

    def test_missing_games_filtered(self):
        raw = {**SAMPLE_CARDS_RAW[0]}
        del raw["games"]
        assert _parse_card(raw) is None


# ---------------------------------------------------------------------------
# parse_bulk_cards
# ---------------------------------------------------------------------------


class TestParseBulkCards:
    def test_parses_fixture_file(self, sample_json_file: Path):
        """Should yield exactly 3 cards (2 filtered out)."""
        cards = list(parse_bulk_cards(sample_json_file))
        assert len(cards) == 3

    def test_yields_correct_cards(self, sample_json_file: Path):
        names = [c.name_en for c in parse_bulk_cards(sample_json_file)]
        assert "Lightning Bolt" in names
        assert "Counterspell" in names
        assert "Black Lotus" in names

    def test_filters_arena_only(self, sample_json_file: Path):
        names = [c.name_en for c in parse_bulk_cards(sample_json_file)]
        assert "Arena Exclusive" not in names

    def test_filters_non_english(self, sample_json_file: Path):
        names = [c.name_en for c in parse_bulk_cards(sample_json_file)]
        assert "Raio" not in names

    def test_returns_iterator(self, sample_json_file: Path):
        result = parse_bulk_cards(sample_json_file)
        # Should be a generator/iterator, not a list
        assert hasattr(result, "__next__")

    def test_empty_file_array(self, tmp_path: Path):
        f = tmp_path / "empty.json"
        f.write_text("[]", encoding="utf-8")
        assert list(parse_bulk_cards(f)) == []

    def test_fallback_when_ijson_not_available(self, sample_json_file: Path):
        """When ijson import fails, should fall back to json.load."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "ijson":
                raise ImportError("No module named 'ijson'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            cards = list(parse_bulk_cards(sample_json_file))
            assert len(cards) == 3


# ---------------------------------------------------------------------------
# _get_download_url
# ---------------------------------------------------------------------------


class TestGetDownloadUrl:
    def test_returns_default_cards_url(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = BULK_API_RESPONSE
        mock_resp.raise_for_status = MagicMock()

        with patch("src.catalog.scryfall.httpx.get", return_value=mock_resp):
            url, size = _get_download_url()

        assert url == "https://example.com/default-cards.json"
        assert size == 150_000_000

    def test_raises_if_no_default_cards(self):
        response_data = {
            "data": [{"type": "oracle_cards", "download_uri": "https://example.com/oracle.json"}]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = response_data
        mock_resp.raise_for_status = MagicMock()

        with patch("src.catalog.scryfall.httpx.get", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="no 'default_cards' entry"):
                _get_download_url()


# ---------------------------------------------------------------------------
# download_bulk_data
# ---------------------------------------------------------------------------


class TestDownloadBulkData:
    def test_skip_if_file_exists_today(self, tmp_path: Path):
        """Should skip download if today's file already exists."""
        from datetime import date

        today = date.today().isoformat()
        existing = tmp_path / f"scryfall-default-cards-{today}.json"
        existing.write_text('["dummy"]', encoding="utf-8")

        result = download_bulk_data(tmp_path)
        assert result == existing

    def test_downloads_file_on_success(self, tmp_path: Path):
        """Should download file and return its path."""
        mock_get_url = patch(
            "src.catalog.scryfall._get_download_url",
            return_value=("https://example.com/cards.json", 100),
        )

        chunk_data = b'[{"name":"Test"}]'
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"content-length": str(len(chunk_data))}
        mock_response.iter_bytes.return_value = [chunk_data]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_stream = patch("src.catalog.scryfall.httpx.stream", return_value=mock_response)

        with mock_get_url, mock_stream:
            result = download_bulk_data(tmp_path)

        assert result.exists()
        assert result.stat().st_size > 0
        assert result.name.startswith("scryfall-default-cards-")
        assert result.read_bytes() == chunk_data

    def test_retries_on_failure(self, tmp_path: Path):
        """Should retry up to 3 times on transient errors."""
        mock_get_url = patch(
            "src.catalog.scryfall._get_download_url",
            return_value=("https://example.com/cards.json", 100),
        )

        call_count = 0

        def fake_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("connection failed")
            # Success on 3rd attempt
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.headers = {"content-length": "10"}
            mock_resp.iter_bytes.return_value = [b'["ok_data"]']
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        mock_stream = patch("src.catalog.scryfall.httpx.stream", side_effect=fake_stream)

        with mock_get_url, mock_stream:
            result = download_bulk_data(tmp_path)

        assert call_count == 3
        assert result.exists()

    def test_raises_after_max_retries(self, tmp_path: Path):
        """Should raise RuntimeError after exhausting retries."""
        mock_get_url = patch(
            "src.catalog.scryfall._get_download_url",
            return_value=("https://example.com/cards.json", 100),
        )
        mock_stream = patch(
            "src.catalog.scryfall.httpx.stream",
            side_effect=httpx.ConnectError("connection failed"),
        )

        with mock_get_url, mock_stream:
            with pytest.raises(RuntimeError, match="Failed to download.*3 attempts"):
                download_bulk_data(tmp_path)

    def test_creates_dest_dir_if_missing(self, tmp_path: Path):
        """Should create destination directory if it doesn't exist."""
        dest = tmp_path / "nested" / "catalog"

        mock_get_url = patch(
            "src.catalog.scryfall._get_download_url",
            return_value=("https://example.com/cards.json", 100),
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"content-length": "5"}
        mock_response.iter_bytes.return_value = [b"[{}]"]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_stream = patch("src.catalog.scryfall.httpx.stream", return_value=mock_response)

        with mock_get_url, mock_stream:
            result = download_bulk_data(dest)

        assert dest.exists()
        assert result.exists()


# ---------------------------------------------------------------------------
# _cleanup_old_files
# ---------------------------------------------------------------------------


class TestCleanupOldFiles:
    def test_keeps_newest_files(self, tmp_path: Path):
        import time

        files = []
        for i in range(4):
            f = tmp_path / f"scryfall-default-cards-2026-01-0{i + 1}.json"
            f.write_text("[]")
            time.sleep(0.05)  # ensure different mtime
            files.append(f)

        _cleanup_old_files(tmp_path)

        remaining = list(tmp_path.glob("scryfall-default-cards-*.json"))
        assert len(remaining) == 2
        # Newest 2 should survive
        assert files[3] in remaining
        assert files[2] in remaining

    def test_no_op_when_fewer_than_limit(self, tmp_path: Path):
        f = tmp_path / "scryfall-default-cards-2026-01-01.json"
        f.write_text("[]")

        _cleanup_old_files(tmp_path)
        assert f.exists()

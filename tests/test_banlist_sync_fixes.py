"""Tests for F213-T03: banlist sync bug fixes.

Covers JSONL.gz parsing, diff-only writes, 0-match failure mode,
and map_to_scryfall_set_code() mapping used during sync.
"""

from __future__ import annotations

import gzip
import json
from datetime import date

import httpx
import pytest
from sqlalchemy.orm import Session

from src.collectors.banlist_sync import (
    _build_index_keys,
    _classify,
    _parse_bulk_line,
    _select_download_url,
    run_banlist_sync,
)
from src.database.models import (
    Base,
    CardLegalityRow,
    CardRow,
    LegalityHistoryRow,
    UserCollectionRow,
)
from src.database.repository import Repository
from src.utils.set_code_map import map_to_scryfall_set_code

# ---------------------------------------------------------------------------
# Helpers (shared across test classes)
# ---------------------------------------------------------------------------


class _ChunkedStream(httpx.AsyncByteStream):
    """Yields bytes in fixed-size chunks to exercise buffer reassembly."""

    def __init__(self, data: bytes, chunk_size: int = 4096):
        self._data = data
        self._chunk_size = chunk_size

    async def __aiter__(self):
        for i in range(0, len(self._data), self._chunk_size):
            yield self._data[i : i + self._chunk_size]


def _catalog_response(download_url: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"data": [{"type": "default_cards", "download_uri": download_url}]},
    )


def _catalog_response_jsonl(download_url: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "data": [
                {
                    "type": "default_cards",
                    "download_uri": "https://data.example/cards.json",
                    "jsonl_download_uri": download_url,
                }
            ]
        },
    )


def _make_transport(
    download_url: str,
    body: bytes,
    chunk_size: int = 4096,
    use_jsonl_field: bool = False,
):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == "https://api.scryfall.com/bulk-data":
            if use_jsonl_field:
                return _catalog_response_jsonl(download_url)
            return _catalog_response(download_url)
        if url == download_url:
            return httpx.Response(200, stream=_ChunkedStream(body, chunk_size))
        raise AssertionError(f"unexpected request to {url}")

    return httpx.MockTransport(handler)


_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _patch_client(monkeypatch, transport):
    def factory(**kwargs):
        kwargs["transport"] = transport
        return _REAL_ASYNC_CLIENT(**kwargs)

    monkeypatch.setattr("src.collectors.banlist_sync.httpx.AsyncClient", factory)


def _cards_jsonl(cards: list[dict]) -> bytes:
    return b"\n".join(json.dumps(c).encode() for c in cards) + b"\n"


SAMPLE_CARDS = [
    {
        "set": "tst",
        "collector_number": "1",
        "legalities": {"commander": "banned", "modern": "legal", "vintage": "legal"},
    },
    {
        "set": "tst",
        "collector_number": "2",
        "legalities": {"vintage": "restricted", "commander": "legal", "modern": "legal"},
    },
    {
        "set": "tst",
        "collector_number": "3",
        "legalities": {"commander": "legal", "modern": "legal", "vintage": "legal"},
    },
]


@pytest.fixture
def db(tmp_path):
    db_url = f"sqlite:///{tmp_path}/t.db"
    repo = Repository(db_url=db_url)
    Base.metadata.create_all(repo.engine)
    return db_url, repo


def _seed_cards(repo: Repository, specs: list[tuple[str, str]]) -> dict[tuple[str, str], int]:
    ids = {}
    with Session(repo.engine) as session:
        for set_code, cn in specs:
            card = CardRow(
                game="magic",
                name_en=f"Card {set_code}{cn}",
                set_code=set_code,
                collector_number=cn,
            )
            session.add(card)
            session.flush()
            ids[(set_code, cn)] = card.id
        session.commit()
    return ids


def _seed_owned(repo: Repository, card_id: int, user_id: str = "u1"):
    with Session(repo.engine) as session:
        session.add(
            UserCollectionRow(
                user_id=user_id,
                card_id=card_id,
                set_code="tst",
                collector_number="1",
                quantity=1,
            )
        )
        session.commit()


# ---------------------------------------------------------------------------
# 1. JSONL.gz parsing tests
# ---------------------------------------------------------------------------


class TestJsonlGzParsing:
    """Verify that the sync handles JSONL, JSONL.gz, and JSON array formats."""

    @pytest.mark.asyncio
    async def test_jsonl_gz_round_trip(self, db, monkeypatch):
        """Create gzipped JSONL fixture, run sync, verify legalities written."""
        db_url, repo = db
        ids = _seed_cards(repo, [("tst", "1"), ("tst", "2")])

        cards = SAMPLE_CARDS[:2]
        raw_jsonl = _cards_jsonl(cards)
        compressed = gzip.compress(raw_jsonl)

        transport = _make_transport("https://data.example/cards.jsonl.gz", compressed)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 0
        assert summary.cards_processed == 2
        with Session(repo.engine) as session:
            rows = session.query(CardLegalityRow).all()
        by_key = {(r.card_id, r.format): r.status for r in rows}
        assert by_key[(ids[("tst", "1")], "commander")] == "banned"
        assert by_key[(ids[("tst", "2")], "vintage")] == "restricted"

    @pytest.mark.asyncio
    async def test_gz_magic_bytes_detected_without_suffix(self, db, monkeypatch):
        """Gzip detected from magic bytes even when URL has no .gz extension."""
        db_url, repo = db
        _seed_cards(repo, [("tst", "1")])

        cards = [SAMPLE_CARDS[0]]
        compressed = gzip.compress(_cards_jsonl(cards))
        # URL does NOT end in .gz -- must detect from magic bytes
        transport = _make_transport("https://data.example/cards.jsonl", compressed, chunk_size=2)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 0
        assert summary.cards_processed == 1

    @pytest.mark.asyncio
    async def test_jsonl_download_uri_preferred_over_download_uri(self, db, monkeypatch):
        """When catalog has both download_uri and jsonl_download_uri, prefer JSONL."""
        db_url, repo = db
        _seed_cards(repo, [("tst", "1")])

        cards = [SAMPLE_CARDS[0]]
        body = _cards_jsonl(cards)
        transport = _make_transport(
            "https://data.example/cards.jsonl",
            body,
            use_jsonl_field=True,
        )
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 0
        assert summary.cards_processed == 1

    @pytest.mark.asyncio
    async def test_gz_with_small_chunks_reassembles_lines(self, db, monkeypatch):
        """Tiny chunk sizes force buffer reassembly mid-line in gzip stream."""
        db_url, repo = db
        _seed_cards(repo, [("tst", "1"), ("tst", "2"), ("tst", "3")])

        compressed = gzip.compress(_cards_jsonl(SAMPLE_CARDS))
        # Chunk size of 3 bytes will split in the middle of compressed data
        transport = _make_transport("https://data.example/cards.jsonl.gz", compressed, chunk_size=3)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 0
        assert summary.cards_processed == 3

    def test_parse_bulk_line_jsonl(self):
        """Plain JSONL line parses correctly."""
        line = b'{"set":"tst","collector_number":"1","legalities":{"commander":"banned"}}'
        result = _parse_bulk_line(line)
        assert result["set"] == "tst"
        assert result["legalities"]["commander"] == "banned"

    def test_parse_bulk_line_json_array_element(self):
        """JSON array element with trailing comma parses correctly."""
        line = b'{"set":"tst","collector_number":"1","legalities":{"commander":"banned"}},'
        result = _parse_bulk_line(line)
        assert result["set"] == "tst"

    def test_parse_bulk_line_array_brackets_return_none(self):
        assert _parse_bulk_line(b"[") is None
        assert _parse_bulk_line(b"]") is None
        assert _parse_bulk_line(b"") is None


# ---------------------------------------------------------------------------
# 2. Diff logic tests: new inserted, unchanged skipped, changed updated
# ---------------------------------------------------------------------------


class TestDiffLogic:
    """Verify that the diff-only write strategy works correctly."""

    @pytest.mark.asyncio
    async def test_new_rows_inserted_on_first_sync(self, db, monkeypatch):
        """First sync inserts new legality rows for banned/restricted cards."""
        db_url, repo = db
        _seed_cards(repo, [("tst", "1"), ("tst", "2")])

        body = _cards_jsonl(SAMPLE_CARDS[:2])
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        # Card 1: commander=banned -> written; modern/vintage=legal -> skipped (compact)
        # Card 2: vintage=restricted -> written; commander=legal, modern=legal -> not written
        assert summary.legalities_upserted == 2
        assert summary.changes_detected == 2  # baseline history entries

    @pytest.mark.asyncio
    async def test_unchanged_rows_skipped_on_second_sync(self, db, monkeypatch):
        """Second sync with identical data writes zero rows."""
        db_url, repo = db
        _seed_cards(repo, [("tst", "1"), ("tst", "2")])

        body = _cards_jsonl(SAMPLE_CARDS[:2])
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        # First sync
        await run_banlist_sync(db_url=db_url, bulk=True)

        # Second sync with same data
        summary2 = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary2.legalities_upserted == 0
        assert summary2.changes_detected == 0

    @pytest.mark.asyncio
    async def test_changed_rows_updated_with_history(self, db, monkeypatch):
        """When a status changes between syncs, only the changed row is updated."""
        db_url, repo = db
        ids = _seed_cards(repo, [("tst", "1"), ("tst", "2")])

        body = _cards_jsonl(SAMPLE_CARDS[:2])
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        # First sync: card 1 is banned in commander
        await run_banlist_sync(db_url=db_url, bulk=True)

        # Second sync: card 1 is now legal in commander
        unbanned_cards = [
            {
                "set": "tst",
                "collector_number": "1",
                "legalities": {"commander": "legal", "modern": "legal", "vintage": "legal"},
            },
            SAMPLE_CARDS[1],
        ]
        body2 = _cards_jsonl(unbanned_cards)
        transport2 = _make_transport("https://data.example/cards.jsonl", body2)
        _patch_client(monkeypatch, transport2)

        summary2 = await run_banlist_sync(db_url=db_url, bulk=True)

        # Only the changed row (card 1, commander: banned->legal) should be written
        assert summary2.legalities_upserted == 1
        assert summary2.changes_detected == 1

        # Verify the actual DB state
        with Session(repo.engine) as session:
            row = (
                session.query(CardLegalityRow)
                .filter_by(card_id=ids[("tst", "1")], format="commander")
                .one()
            )
            assert row.status == "legal"

            # History should show the transition
            history = (
                session.query(LegalityHistoryRow)
                .filter_by(card_id=ids[("tst", "1")], format="commander")
                .order_by(LegalityHistoryRow.id.desc())
                .first()
            )
            assert history.old_status == "banned"
            assert history.new_status == "legal"
            assert history.source == "scryfall_sync"

    @pytest.mark.asyncio
    async def test_compact_scope_only_stores_banned_restricted_owned(self, db, monkeypatch):
        """Compact scope: only banned/restricted + owned cards get legality rows."""
        db_url, repo = db
        ids = _seed_cards(repo, [("tst", "1"), ("tst", "2"), ("tst", "3")])
        # Mark card 3 as owned
        _seed_owned(repo, ids[("tst", "3")])

        body = _cards_jsonl(SAMPLE_CARDS)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True, scope="compact")

        assert summary.errors == 0
        with Session(repo.engine) as session:
            # Card 1: commander=banned -> stored
            assert (
                session.query(CardLegalityRow)
                .filter_by(card_id=ids[("tst", "1")], format="commander")
                .count()
                == 1
            )
            # Card 1: modern=legal, not owned, not existing -> NOT stored
            assert (
                session.query(CardLegalityRow)
                .filter_by(card_id=ids[("tst", "1")], format="modern")
                .count()
                == 0
            )
            # Card 3: all legal, but OWNED -> all formats stored
            card3_rows = session.query(CardLegalityRow).filter_by(card_id=ids[("tst", "3")]).all()
            assert {r.format for r in card3_rows} == {"commander", "modern", "vintage"}

    def test_classify_unchanged_returns_no_write(self):
        """_classify returns write=False when status hasn't changed."""
        write, change, eff = _classify(1, "commander", "banned", "banned", False, False, "compact")
        assert write is False
        assert change is None

    def test_classify_changed_returns_write_with_change(self):
        """_classify returns write=True with a LegalityChange when status changed."""
        write, change, eff = _classify(1, "commander", "legal", "banned", False, False, "compact")
        assert write is True
        assert change is not None
        assert change.old_status == "banned"
        assert change.new_status == "legal"
        assert eff == date.today()

    def test_classify_new_banned_first_sync_baseline(self):
        """First sync: new banned card gets baseline source."""
        write, change, eff = _classify(1, "commander", "banned", None, False, True, "compact")
        assert write is True
        assert change.source == "scryfall_baseline"
        assert eff is None  # No effective_date for baseline

    def test_classify_new_legal_not_owned_compact_no_write(self):
        """Compact scope: legal card, not owned, no existing row -> no write."""
        write, change, eff = _classify(1, "modern", "legal", None, False, True, "compact")
        assert write is False

    def test_classify_owned_card_always_stored(self):
        """Owned cards always get their legality stored regardless of status."""
        write, change, eff = _classify(1, "modern", "legal", None, True, True, "compact")
        assert write is True
        assert change is None  # No change, just storage


# ---------------------------------------------------------------------------
# 3. 0-match failure mode tests
# ---------------------------------------------------------------------------


class TestZeroMatchFailure:
    """Verify that 0 parsed lines or 0 matches raise RuntimeError."""

    @pytest.mark.asyncio
    async def test_zero_lines_parsed_raises(self, db, monkeypatch):
        """Empty bulk file (0 parseable lines) raises RuntimeError."""
        db_url, repo = db
        _seed_cards(repo, [("tst", "1")])

        body = b""
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        with pytest.raises(RuntimeError, match="parsed 0 lines"):
            await run_banlist_sync(db_url=db_url, bulk=True)

    @pytest.mark.asyncio
    async def test_zero_matches_over_threshold_raises(self, db, monkeypatch):
        """Over 1000 input lines but 0 matches raises RuntimeError."""
        db_url, repo = db
        # Seed a card with a set code that won't match any bulk data
        _seed_cards(repo, [("zzz", "999")])

        # Generate 1001 cards that won't match our local cards
        cards = [{"set": "tst", "collector_number": str(i), "legalities": {}} for i in range(1001)]
        body = _cards_jsonl(cards)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        with pytest.raises(RuntimeError, match="matched 0 cards"):
            await run_banlist_sync(db_url=db_url, bulk=True)

    @pytest.mark.asyncio
    async def test_zero_matches_under_threshold_does_not_raise(self, db, monkeypatch):
        """Under 1000 input lines with 0 matches does NOT raise."""
        db_url, repo = db
        _seed_cards(repo, [("zzz", "999")])

        # Only 5 cards, below the 1000-line threshold
        cards = [{"set": "tst", "collector_number": str(i), "legalities": {}} for i in range(5)]
        body = _cards_jsonl(cards)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.cards_processed == 0
        assert summary.errors == 0

    @pytest.mark.asyncio
    async def test_all_lines_malformed_raises_zero_lines(self, db, monkeypatch):
        """If every line is malformed JSON, parsed_lines stays 0 and raises."""
        db_url, repo = db
        _seed_cards(repo, [("tst", "1")])

        body = b"{bad json\n{also bad\n{nope\n"
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        with pytest.raises(RuntimeError, match="parsed 0 lines"):
            await run_banlist_sync(db_url=db_url, bulk=True)


# ---------------------------------------------------------------------------
# 4. map_to_scryfall_set_code() mapping tests
# ---------------------------------------------------------------------------


class TestMapToScryfallSetCode:
    """Verify Liga/MYP set code normalization used during sync."""

    def test_known_variant_borderless(self):
        assert map_to_scryfall_set_code("bldmr") == "dmr"
        assert map_to_scryfall_set_code("BLDMR") == "dmr"

    def test_known_variant_extended_art(self):
        assert map_to_scryfall_set_code("exdmu") == "dmu"

    def test_known_variant_showcase(self):
        assert map_to_scryfall_set_code("skmh2") == "mh2"

    def test_known_variant_legacy_short_codes(self):
        assert map_to_scryfall_set_code("4e") == "4ed"
        assert map_to_scryfall_set_code("us") == "usg"
        assert map_to_scryfall_set_code("mi") == "mrd"

    def test_secret_lair_normalization(self):
        assert map_to_scryfall_set_code("sld123") == "sld"
        assert map_to_scryfall_set_code("SLD456") == "sld"

    def test_standard_code_passthrough(self):
        assert map_to_scryfall_set_code("dmr") == "dmr"
        assert map_to_scryfall_set_code("tst") == "tst"
        assert map_to_scryfall_set_code("MH3") == "mh3"

    def test_prefix_strip_heuristic(self):
        """Unknown variant codes get prefix stripped as heuristic."""
        # "bl" prefix + "xxx" remainder (3 chars, alphanumeric) -> "xxx"
        assert map_to_scryfall_set_code("blxyz") == "xyz"

    def test_whitespace_handling(self):
        assert map_to_scryfall_set_code("  dmr  ") == "dmr"
        assert map_to_scryfall_set_code(" BLDMR ") == "dmr"

    def test_build_index_keys_includes_mapped_codes(self):
        """_build_index_keys generates keys for both raw and mapped set codes."""
        keys = _build_index_keys("bldmr", "007")
        # Should include raw set code
        assert ("bldmr", "007") in keys
        assert ("bldmr", "7") in keys
        # Should include mapped set code (dmr)
        assert ("dmr", "007") in keys
        assert ("dmr", "7") in keys

    def test_build_index_keys_no_mapping_needed(self):
        """When set code doesn't map to anything different, keys are minimal."""
        keys = _build_index_keys("tst", "1")
        assert keys == {("tst", "1")}

    def test_build_index_keys_zero_padded_cn(self):
        """Collector number zero-stripping produces both variants."""
        keys = _build_index_keys("tst", "000")
        assert ("tst", "000") in keys
        assert ("tst", "0") in keys

    @pytest.mark.asyncio
    async def test_liga_set_code_matched_during_bulk_sync(self, db, monkeypatch):
        """Local card with Liga set code (bldmr) matches Scryfall data (dmr)."""
        db_url, repo = db
        ids = _seed_cards(repo, [("bldmr", "1")])

        cards = [{"set": "dmr", "collector_number": "1", "legalities": {"commander": "banned"}}]
        body = _cards_jsonl(cards)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.cards_processed == 1
        with Session(repo.engine) as session:
            row = session.query(CardLegalityRow).filter_by(card_id=ids[("bldmr", "1")]).one()
        assert row.status == "banned"

    @pytest.mark.asyncio
    async def test_cn_zero_padding_matched_during_bulk_sync(self, db, monkeypatch):
        """Local card with CN '007' matches Scryfall data with CN '7'."""
        db_url, repo = db
        _seed_cards(repo, [("tst", "007")])

        cards = [{"set": "tst", "collector_number": "7", "legalities": {"commander": "banned"}}]
        body = _cards_jsonl(cards)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.cards_processed == 1


# ---------------------------------------------------------------------------
# 5. select_download_url preference tests
# ---------------------------------------------------------------------------


class TestSelectDownloadUrl:
    """Verify URL selection prefers JSONL format."""

    def test_prefers_jsonl_download_uri(self):
        catalog = {
            "data": [
                {
                    "type": "default_cards",
                    "download_uri": "https://x/cards.json",
                    "jsonl_download_uri": "https://x/cards.jsonl",
                }
            ]
        }
        assert _select_download_url(catalog) == "https://x/cards.jsonl"

    def test_falls_back_to_download_uri(self):
        catalog = {"data": [{"type": "default_cards", "download_uri": "https://x/cards.json"}]}
        assert _select_download_url(catalog) == "https://x/cards.json"

    def test_no_default_cards_returns_none(self):
        catalog = {"data": [{"type": "rulings", "download_uri": "https://x/rulings.json"}]}
        assert _select_download_url(catalog) is None

    def test_empty_catalog(self):
        assert _select_download_url({}) is None
        assert _select_download_url({"data": []}) is None


# ---------------------------------------------------------------------------
# 6. follow_redirects configuration test
# ---------------------------------------------------------------------------


class TestFollowRedirects:
    """Verify that the HTTP client follows redirects."""

    @pytest.mark.asyncio
    async def test_redirect_followed_during_bulk_download(self, db, monkeypatch):
        """Bulk download that returns 302 redirect is followed automatically."""
        db_url, repo = db
        _seed_cards(repo, [("tst", "1"), ("tst", "2"), ("tst", "3")])

        body = _cards_jsonl(SAMPLE_CARDS)

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url == "https://api.scryfall.com/bulk-data":
                return _catalog_response("https://data.example/cards.jsonl")
            if url == "https://data.example/cards.jsonl":
                return httpx.Response(
                    302, headers={"Location": "https://cdn.example/redirected.jsonl"}
                )
            if url == "https://cdn.example/redirected.jsonl":
                return httpx.Response(200, stream=_ChunkedStream(body))
            raise AssertionError(f"unexpected request to {url}")

        transport = httpx.MockTransport(handler)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 0
        assert summary.cards_processed == 3

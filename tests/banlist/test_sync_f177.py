"""Tests for F177-T06: banlist_sync bulk-path rewrite."""

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

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestSelectDownloadUrl:
    def test_prefers_jsonl(self):
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

    def test_no_default_cards_entry(self):
        catalog = {"data": [{"type": "rulings", "download_uri": "https://x/rulings.json"}]}
        assert _select_download_url(catalog) is None

    def test_empty_catalog(self):
        assert _select_download_url({}) is None


class TestParseBulkLine:
    def test_blank_line(self):
        assert _parse_bulk_line(b"   ") is None
        assert _parse_bulk_line(b"") is None

    def test_array_brackets(self):
        assert _parse_bulk_line(b"[") is None
        assert _parse_bulk_line(b"]") is None
        assert _parse_bulk_line(b"[\r\n") is None

    def test_trailing_comma_stripped(self):
        result = _parse_bulk_line(b'{"set": "tst", "collector_number": "1"},')
        assert result == {"set": "tst", "collector_number": "1"}

    def test_plain_jsonl_line(self):
        result = _parse_bulk_line(b'{"set": "tst", "collector_number": "1"}')
        assert result == {"set": "tst", "collector_number": "1"}

    def test_crlf_line_ending(self):
        result = _parse_bulk_line(b'{"set": "tst", "collector_number": "1"},\r\n')
        assert result == {"set": "tst", "collector_number": "1"}

    def test_malformed_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_bulk_line(b"{not valid json")


class TestBuildIndexKeys:
    def test_raw_and_mapped_and_cn_variants(self):
        keys = _build_index_keys("bldmr", "007")
        assert ("bldmr", "007") in keys
        assert ("bldmr", "7") in keys
        assert ("dmr", "007") in keys
        assert ("dmr", "7") in keys

    def test_no_mapping_needed(self):
        keys = _build_index_keys("tst", "1")
        assert keys == {("tst", "1")}

    def test_cn_all_zeros(self):
        keys = _build_index_keys("tst", "000")
        assert ("tst", "0") in keys


class TestClassify:
    def test_compact_non_owned_legal_not_stored(self):
        write, change, eff = _classify(1, "modern", "legal", None, False, True, "compact")
        assert write is False
        assert change is None

    def test_compact_banned_stored_first_sync_baseline(self):
        write, change, eff = _classify(1, "commander", "banned", None, False, True, "compact")
        assert write is True
        assert eff is None
        assert change.source == "scryfall_baseline"
        assert change.old_status is None
        assert change.new_status == "banned"

    def test_compact_banned_stored_not_first_sync(self):
        write, change, eff = _classify(1, "commander", "banned", None, False, False, "compact")
        assert write is True
        assert eff == date.today()
        assert change.source == "scryfall_sync"

    def test_compact_owned_card_always_stored(self):
        write, change, eff = _classify(1, "modern", "legal", None, True, True, "compact")
        assert write is True
        assert change is None
        assert eff is None

    def test_compact_existing_row_transition(self):
        write, change, eff = _classify(1, "commander", "legal", "banned", False, False, "compact")
        assert write is True
        assert eff == date.today()
        assert change.old_status == "banned"
        assert change.new_status == "legal"
        assert change.source == "scryfall_sync"

    def test_unchanged_status_skips(self):
        write, change, eff = _classify(1, "commander", "banned", "banned", False, False, "compact")
        assert write is False
        assert change is None

    def test_full_scope_always_stores(self):
        write, change, eff = _classify(1, "modern", "legal", None, False, True, "full")
        assert write is True
        assert change is None

    def test_compact_no_existing_no_owned_not_banned_not_stored(self):
        write, change, eff = _classify(1, "modern", "not_legal", None, False, False, "compact")
        assert write is False


def test_run_banlist_sync_invalid_scope():
    import asyncio

    with pytest.raises(ValueError):
        asyncio.run(run_banlist_sync(db_url="sqlite:///:memory:", scope="bogus"))


# ---------------------------------------------------------------------------
# Integration: bulk sync against a MockTransport
# ---------------------------------------------------------------------------


class _ChunkedStream(httpx.AsyncByteStream):
    """Yields the given bytes in fixed-size chunks, to exercise buffer reassembly."""

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


def _make_transport(download_url: str, body: bytes, chunk_size: int = 4096, redirect: bool = False):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == "https://api.scryfall.com/bulk-data":
            return _catalog_response(download_url)
        if url == download_url:
            if redirect:
                return httpx.Response(302, headers={"Location": "https://data.example/redirected"})
            return httpx.Response(200, stream=_ChunkedStream(body, chunk_size))
        if url == "https://data.example/redirected":
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


def _cards_json_array(cards: list[dict]) -> bytes:
    lines = [b"["]
    for c in cards:
        lines.append(json.dumps(c).encode() + b",")
    lines.append(b"]")
    return b"\n".join(lines)


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


class TestBulkSyncJsonl:
    @pytest.mark.asyncio
    async def test_jsonl_populates_card_legalities(self, db, monkeypatch):
        db_url, repo = db
        ids = _seed_cards(repo, [("tst", "1"), ("tst", "2"), ("tst", "3")])

        body = _cards_jsonl(SAMPLE_CARDS)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 0
        assert summary.cards_processed == 3

        with Session(repo.engine) as session:
            rows = session.query(CardLegalityRow).all()
        by_card_fmt = {(r.card_id, r.format): r.status for r in rows}
        assert by_card_fmt[(ids[("tst", "1")], "commander")] == "banned"
        assert by_card_fmt[(ids[("tst", "2")], "vintage")] == "restricted"
        # card 3 is legal everywhere and not owned -> compact policy stores nothing
        assert (ids[("tst", "3")], "commander") not in by_card_fmt

    @pytest.mark.asyncio
    async def test_gzip_variant_matches_plain(self, db, monkeypatch):
        db_url, repo = db
        ids = _seed_cards(repo, [("tst", "1"), ("tst", "2"), ("tst", "3")])

        body = gzip.compress(_cards_jsonl(SAMPLE_CARDS))
        transport = _make_transport("https://data.example/cards.jsonl.gz", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 0
        with Session(repo.engine) as session:
            rows = session.query(CardLegalityRow).all()
        by_card_fmt = {(r.card_id, r.format): r.status for r in rows}
        assert by_card_fmt[(ids[("tst", "1")], "commander")] == "banned"
        assert by_card_fmt[(ids[("tst", "2")], "vintage")] == "restricted"

    @pytest.mark.asyncio
    async def test_json_array_variant(self, db, monkeypatch):
        db_url, repo = db
        ids = _seed_cards(repo, [("tst", "1"), ("tst", "2"), ("tst", "3")])

        body = _cards_json_array(SAMPLE_CARDS)
        transport = _make_transport("https://data.example/cards.json", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 0
        with Session(repo.engine) as session:
            rows = session.query(CardLegalityRow).all()
        by_card_fmt = {(r.card_id, r.format): r.status for r in rows}
        assert by_card_fmt[(ids[("tst", "1")], "commander")] == "banned"

    @pytest.mark.asyncio
    async def test_chunk_split_line_reassembled(self, db, monkeypatch):
        db_url, repo = db
        _seed_cards(repo, [("tst", "1")])

        body = _cards_jsonl([SAMPLE_CARDS[0]])
        transport = _make_transport("https://data.example/cards.jsonl", body, chunk_size=7)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 0
        assert summary.cards_processed == 1

    @pytest.mark.asyncio
    async def test_redirect_followed(self, db, monkeypatch):
        db_url, repo = db
        _seed_cards(repo, [("tst", "1"), ("tst", "2"), ("tst", "3")])

        body = _cards_jsonl(SAMPLE_CARDS)
        transport = _make_transport("https://data.example/cards.jsonl", body, redirect=True)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 0
        assert summary.cards_processed == 3

    @pytest.mark.asyncio
    async def test_liga_style_set_code_maps(self, db, monkeypatch):
        db_url, repo = db
        # "bldmr" maps to "dmr" per set_code_map.py
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
    async def test_collector_number_leading_zero(self, db, monkeypatch):
        db_url, repo = db
        ids = _seed_cards(repo, [("tst", "007")])

        cards = [{"set": "tst", "collector_number": "7", "legalities": {"commander": "banned"}}]
        body = _cards_jsonl(cards)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.cards_processed == 1
        with Session(repo.engine) as session:
            row = session.query(CardLegalityRow).filter_by(card_id=ids[("tst", "007")]).one()
        assert row.status == "banned"

    @pytest.mark.asyncio
    async def test_two_local_ids_same_scryfall_key_both_written(self, db, monkeypatch):
        db_url, repo = db
        with Session(repo.engine) as session:
            c1 = CardRow(game="magic", name_en="Dup 1", set_code="tst", collector_number="1")
            c2 = CardRow(game="magic", name_en="Dup 2", set_code="tst", collector_number="01")
            session.add_all([c1, c2])
            session.commit()
            id1, id2 = c1.id, c2.id

        cards = [{"set": "tst", "collector_number": "1", "legalities": {"commander": "banned"}}]
        body = _cards_jsonl(cards)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.cards_processed == 2
        with Session(repo.engine) as session:
            rows = (
                session.query(CardLegalityRow)
                .filter(CardLegalityRow.card_id.in_([id1, id2]))
                .all()
            )
        assert {r.card_id for r in rows} == {id1, id2}

    @pytest.mark.asyncio
    async def test_malformed_line_counts_error_and_continues(self, db, monkeypatch):
        db_url, repo = db
        _seed_cards(repo, [("tst", "1")])

        good = json.dumps(SAMPLE_CARDS[0]).encode()
        body = good + b"\n{not valid json\n"
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 1
        assert summary.cards_processed == 1

    @pytest.mark.asyncio
    async def test_no_default_cards_entry_sets_error_no_raise(self, db, monkeypatch):
        db_url, repo = db
        _seed_cards(repo, [("tst", "1")])

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": [{"type": "rulings", "download_uri": "x"}]})

        transport = httpx.MockTransport(handler)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 1

    @pytest.mark.asyncio
    async def test_zero_matches_over_threshold_raises(self, db, monkeypatch):
        db_url, repo = db
        _seed_cards(repo, [("zzz", "999")])

        cards = [{"set": "tst", "collector_number": str(i), "legalities": {}} for i in range(1001)]
        body = _cards_jsonl(cards)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        with pytest.raises(RuntimeError, match="matched 0 cards"):
            await run_banlist_sync(db_url=db_url, bulk=True)

    @pytest.mark.asyncio
    async def test_zero_lines_raises(self, db, monkeypatch):
        db_url, repo = db
        _seed_cards(repo, [("tst", "1")])

        body = b""
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        with pytest.raises(RuntimeError, match="parsed 0 lines"):
            await run_banlist_sync(db_url=db_url, bulk=True)

    @pytest.mark.asyncio
    async def test_limit_caps_matched_cards(self, db, monkeypatch):
        db_url, repo = db
        _seed_cards(repo, [("tst", "1"), ("tst", "2"), ("tst", "3")])

        body = _cards_jsonl(SAMPLE_CARDS)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True, limit=1)

        assert summary.cards_processed == 1

    @pytest.mark.asyncio
    async def test_owned_card_stores_all_formats(self, db, monkeypatch):
        db_url, repo = db
        ids = _seed_cards(repo, [("tst", "1"), ("tst", "2"), ("tst", "3")])
        _seed_owned(repo, ids[("tst", "3")])

        body = _cards_jsonl(SAMPLE_CARDS)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 0
        with Session(repo.engine) as session:
            rows = session.query(CardLegalityRow).filter_by(card_id=ids[("tst", "3")]).all()
        formats = {r.format for r in rows}
        assert formats == {"commander", "modern", "vintage"}

    @pytest.mark.asyncio
    async def test_scope_full_stores_every_format(self, db, monkeypatch):
        db_url, repo = db
        ids = _seed_cards(repo, [("tst", "1"), ("tst", "2"), ("tst", "3")])

        body = _cards_jsonl(SAMPLE_CARDS)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True, scope="full")

        assert summary.errors == 0
        with Session(repo.engine) as session:
            rows = session.query(CardLegalityRow).filter_by(card_id=ids[("tst", "3")]).all()
        formats = {r.format for r in rows}
        assert formats == {"commander", "modern", "vintage"}

    @pytest.mark.asyncio
    async def test_first_run_history_only_banned_restricted_baseline(self, db, monkeypatch):
        db_url, repo = db
        _seed_cards(repo, [("tst", "1"), ("tst", "2"), ("tst", "3")])

        body = _cards_jsonl(SAMPLE_CARDS)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        await run_banlist_sync(db_url=db_url, bulk=True)

        with Session(repo.engine) as session:
            history = session.query(LegalityHistoryRow).all()
        assert len(history) == 2
        for h in history:
            assert h.source == "scryfall_baseline"
            assert h.old_status is None
            assert h.new_status in ("banned", "restricted")

    @pytest.mark.asyncio
    async def test_second_run_no_changes_zero_upserts_zero_history(self, db, monkeypatch):
        db_url, repo = db
        _seed_cards(repo, [("tst", "1"), ("tst", "2"), ("tst", "3")])

        body = _cards_jsonl(SAMPLE_CARDS)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        await run_banlist_sync(db_url=db_url, bulk=True)
        summary2 = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary2.legalities_upserted == 0
        assert summary2.changes_detected == 0

    @pytest.mark.asyncio
    async def test_second_run_transition_updates_and_adds_history(self, db, monkeypatch):
        db_url, repo = db
        ids = _seed_cards(repo, [("tst", "1"), ("tst", "2"), ("tst", "3")])

        body = _cards_jsonl(SAMPLE_CARDS)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)
        await run_banlist_sync(db_url=db_url, bulk=True)

        unbanned_cards = [
            {
                "set": "tst",
                "collector_number": "1",
                "legalities": {"commander": "legal", "modern": "legal", "vintage": "legal"},
            },
            SAMPLE_CARDS[1],
            SAMPLE_CARDS[2],
        ]
        body2 = _cards_jsonl(unbanned_cards)
        transport2 = _make_transport("https://data.example/cards.jsonl", body2)
        _patch_client(monkeypatch, transport2)
        summary2 = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary2.legalities_upserted == 1
        assert summary2.changes_detected == 1

        with Session(repo.engine) as session:
            row = (
                session.query(CardLegalityRow)
                .filter_by(card_id=ids[("tst", "1")], format="commander")
                .one()
            )
            assert row.status == "legal"
            history = (
                session.query(LegalityHistoryRow)
                .filter_by(card_id=ids[("tst", "1")], format="commander")
                .filter(LegalityHistoryRow.source == "scryfall_sync")
                .all()
            )
        assert len(history) == 1
        assert history[0].old_status == "banned"
        assert history[0].new_status == "legal"

    def test_comma_only_line_is_skipped(self):
        assert _parse_bulk_line(b",") is None

    @pytest.mark.asyncio
    async def test_gzip_magic_byte_fallback_without_gz_suffix(self, db, monkeypatch):
        db_url, repo = db
        ids = _seed_cards(repo, [("tst", "1")])

        cards = [{"set": "tst", "collector_number": "1", "legalities": {"commander": "banned"}}]
        body = gzip.compress(_cards_jsonl(cards))
        # No ".gz" suffix on the URL -> gzip must be detected from magic bytes.
        transport = _make_transport("https://data.example/cards.jsonl", body, chunk_size=2)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 0
        assert summary.cards_processed == 1
        with Session(repo.engine) as session:
            row = session.query(CardLegalityRow).filter_by(card_id=ids[("tst", "1")]).one()
        assert row.status == "banned"

    @pytest.mark.asyncio
    async def test_limit_with_multiple_ids_per_line(self, db, monkeypatch):
        db_url, repo = db
        with Session(repo.engine) as session:
            c1 = CardRow(game="magic", name_en="Dup 1", set_code="tst", collector_number="1")
            c2 = CardRow(game="magic", name_en="Dup 2", set_code="tst", collector_number="01")
            session.add_all([c1, c2])
            session.commit()

        cards = [{"set": "tst", "collector_number": "1", "legalities": {"commander": "banned"}}]
        body = _cards_jsonl(cards)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True, limit=1)

        assert summary.cards_processed == 1

    @pytest.mark.asyncio
    async def test_mid_stream_flush(self, db, monkeypatch):
        import src.collectors.banlist_sync as bs

        monkeypatch.setattr(bs, "FLUSH_EVERY", 2)

        db_url, repo = db
        specs = [("tst", str(i)) for i in range(3)]
        _seed_cards(repo, specs)

        cards = [
            {"set": "tst", "collector_number": str(i), "legalities": {"commander": "banned"}}
            for i in range(3)
        ]
        body = _cards_jsonl(cards)
        transport = _make_transport("https://data.example/cards.jsonl", body)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=True)

        assert summary.errors == 0
        assert summary.cards_processed == 3
        assert summary.legalities_upserted == 3


class TestPerCardSync:
    @staticmethod
    def _make_percard_transport(responses: dict[str, httpx.Response]):
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url in responses:
                return responses[url]
            raise AssertionError(f"unexpected request to {url}")

        return httpx.MockTransport(handler)

    @pytest.mark.asyncio
    async def test_happy_path_writes_banned(self, db, monkeypatch):
        db_url, repo = db
        ids = _seed_cards(repo, [("tst", "1")])

        url = "https://api.scryfall.com/cards/tst/1"
        legalities = {"commander": "banned", "modern": "legal"}
        responses = {url: httpx.Response(200, json={"legalities": legalities})}
        transport = self._make_percard_transport(responses)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=False)

        assert summary.errors == 0
        assert summary.cards_processed == 1
        with Session(repo.engine) as session:
            row = session.query(CardLegalityRow).filter_by(card_id=ids[("tst", "1")]).one()
        assert row.status == "banned"

    @pytest.mark.asyncio
    async def test_maps_liga_set_code_in_url(self, db, monkeypatch):
        db_url, repo = db
        _seed_cards(repo, [("bldmr", "1")])

        url = "https://api.scryfall.com/cards/dmr/1"
        responses = {url: httpx.Response(200, json={"legalities": {"commander": "banned"}})}
        transport = self._make_percard_transport(responses)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=False)

        assert summary.cards_processed == 1
        assert summary.errors == 0

    @pytest.mark.asyncio
    async def test_404_is_skipped(self, db, monkeypatch):
        db_url, repo = db
        _seed_cards(repo, [("tst", "1")])

        url = "https://api.scryfall.com/cards/tst/1"
        responses = {url: httpx.Response(404)}
        transport = self._make_percard_transport(responses)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=False)

        assert summary.cards_processed == 0
        assert summary.errors == 0

    @pytest.mark.asyncio
    async def test_server_error_counts_as_error(self, db, monkeypatch):
        db_url, repo = db
        _seed_cards(repo, [("tst", "1")])

        url = "https://api.scryfall.com/cards/tst/1"
        responses = {url: httpx.Response(500)}
        transport = self._make_percard_transport(responses)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=False)

        assert summary.cards_processed == 0
        assert summary.errors == 1

    @pytest.mark.asyncio
    async def test_no_local_cards_returns_early(self, db, monkeypatch):
        db_url, repo = db

        summary = await run_banlist_sync(db_url=db_url, bulk=False)

        assert summary.cards_processed == 0
        assert summary.errors == 0

    @pytest.mark.asyncio
    async def test_owned_card_stores_legal_format_too(self, db, monkeypatch):
        db_url, repo = db
        ids = _seed_cards(repo, [("tst", "1")])
        _seed_owned(repo, ids[("tst", "1")])

        url = "https://api.scryfall.com/cards/tst/1"
        responses = {
            url: httpx.Response(200, json={"legalities": {"commander": "legal", "modern": "legal"}})
        }
        transport = self._make_percard_transport(responses)
        _patch_client(monkeypatch, transport)

        summary = await run_banlist_sync(db_url=db_url, bulk=False)

        assert summary.errors == 0
        with Session(repo.engine) as session:
            rows = session.query(CardLegalityRow).filter_by(card_id=ids[("tst", "1")]).all()
        assert {r.format for r in rows} == {"commander", "modern"}


@pytest.mark.asyncio
async def test_bulk_sync_no_local_cards_returns_early(db, monkeypatch):
    db_url, repo = db
    # No cards seeded at all -> card_index is empty.

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"data": [{"type": "default_cards", "download_uri": "https://x/cards.jsonl"}]}
        )

    transport = httpx.MockTransport(handler)
    _patch_client(monkeypatch, transport)

    summary = await run_banlist_sync(db_url=db_url, bulk=True)

    assert summary.cards_processed == 0
    assert summary.errors == 0

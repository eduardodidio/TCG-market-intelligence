# 01 — Sync fix (backend collector + writer)

## Files
- NEW `src/database/legality_writer.py` (F177-T03)
- EDIT `src/collectors/banlist_sync.py` (F177-T06)
- Tests: NEW `tests/banlist/test_legality_writer.py`, NEW `tests/banlist/test_sync_f177.py`;
  keep `tests/banlist/test_sync.py` green (update only assertions that encode the old buggy behavior)

## legality_writer.py contract (F177-T03)
```python
from sqlalchemy import Engine
from src.domain.models import CardLegality, LegalityChange

CHUNK_SIZE = 500

def bulk_upsert_legalities(engine: Engine, legalities: list[CardLegality],
                           chunk_size: int = CHUNK_SIZE) -> int:
    """Multi-row INSERT ... ON CONFLICT (card_id, format) DO UPDATE, chunked.
    One statement per chunk (not per row). Uses compat.dialect_insert(engine, CardLegalityRow)
    with .values(list_of_dicts). Returns number of rows sent. Deduplicates by
    (card_id, format) inside a chunk (last wins) — PG rejects duplicate keys in one statement."""

def bulk_insert_legality_changes(engine: Engine, changes: list[LegalityChange],
                                 chunk_size: int = CHUNK_SIZE) -> int:
    """session.execute(insert(LegalityHistoryRow), [dicts]) per chunk. Returns count."""
```
- Use `datetime.now()` for `updated_at`. `effective_date` can be None.
- Do NOT change `Repository.upsert_legalities` / `insert_legality_changes`
  (other code/tests use them). The sync switches to the new functions.

## banlist_sync.py changes (F177-T06)
1. **Download URL selection**: from `/bulk-data` entry `type == "default_cards"`,
   prefer `jsonl_download_uri`, fall back to `download_uri` (same as `src/catalog/scryfall.py:_get_download_url`).
2. **Client**: `httpx.AsyncClient(timeout=300, follow_redirects=True)`. Send a
   `User-Agent: TEDHC-Market/1.0` and an `Accept: application/json` header (Scryfall requires them).
3. **Decoding**: if the URL ends with `.gz` OR the first 2 bytes are `\x1f\x8b`,
   stream-decompress with `zlib.decompressobj(wbits=16 + zlib.MAX_WBITS)` chunk
   by chunk. Do NOT buffer the whole file in memory.
4. **Line parsing** via a new pure helper `_parse_bulk_line(line: bytes) -> dict | None`:
   strip whitespace; skip empty, `[`, `]`; strip one trailing `,`; `json.loads`;
   return None on JSONDecodeError (count in `summary.errors`).
5. **Buffering**: replace the O(n²) `buffer += chunk; split(b"\n", 1)` loop with
   `lines = buffer.split(b"\n"); buffer = lines.pop()`.
6. **Card index**: new pure helper `_build_index_keys(set_code, collector_number) -> set[tuple[str,str]]`
   that returns keys for: (raw lower set, cn lower), (map_to_scryfall_set_code(set).lower(), cn lower),
   and the same pair with `cn.lstrip("0") or "0"`. Index every key → card_id.
   Keep a list: one Scryfall card can map to one or more local ids (use `dict[key, list[int]]`).
7. **Compact storage policy** (default; `run_banlist_sync(..., scope="compact")`,
   with `"full"` storing everything). For each (card_id, fmt, status), write only when:
   - `status in {"banned","restricted"}`, OR
   - `card_id in owned_card_ids` (any `user_collection.card_id`, all users — the legality panel needs every format), OR
   - an existing row for (card_id, fmt) exists (so transitions like banned→legal get updated).
   `scope` is a keyword param of `run_banlist_sync`. The CLI does NOT change (it uses the default "compact").
8. **Diff-only**: skip the write when the existing status == the new status.
9. **Baseline / history policy**:
   - `first_sync = (existing_legalities is empty)`.
   - The existing row differs → change row (`old_status=existing`, source `"scryfall_sync"`), `effective_date=today`.
   - No existing row AND status in {banned, restricted}:
     - first_sync → history row with `old_status=None`, `source="scryfall_baseline"`, `effective_date=None`
     - not first_sync → history row with `old_status=None`, `source="scryfall_sync"`, `effective_date=today`
   - No existing row AND status legal/not_legal → **no** history row.
   `LegalityChange` already has a `source` field (see `repository.insert_legality_changes`, which uses `c.source`).
10. **Fail loudly (RC7)**: after streaming, if `card_index` is non-empty and
    `cards_matched == 0` and more than 1000 lines were parsed → `raise RuntimeError("banlist_sync matched 0 cards — check set-code mapping / bulk format")`.
    If `parsed_lines == 0` → raise `RuntimeError("banlist_sync parsed 0 lines from bulk file")`.
11. Write with `legality_writer.bulk_upsert_legalities(repo.engine, …)` /
    `bulk_insert_legality_changes`. Flush in batches of ~5000 while streaming (bounded memory).
12. Log the diagnostics with structlog: `banlist_sync_diagnostics` with `lines_parsed`,
    `cards_matched`, `rows_written`, `changes`, `skipped_unchanged`.
13. The per-card mode (`_sync_per_card`) gets the same policy (reuse a shared
    `_classify(card_id, fmt, status, existing, owned, first_sync, scope)` pure helper).
    Map the set code with `map_to_scryfall_set_code` in the URL.

## Pure helpers (must be unit-tested without network)
`_parse_bulk_line`, `_build_index_keys`, `_classify` (returns `(write: bool, change: LegalityChange | None, effective_date)`).

## Testing notes
- Mock the network with `httpx.MockTransport`, or monkeypatch `httpx.AsyncClient` (see
  the existing `tests/banlist/test_sync.py` for the fixtures used there).
- SQLite in-memory/tmp DB via `Repository("sqlite:///<tmp_path>/t.db")`. Create
  tables the same way the existing banlist tests do.
- Gzip fixture: `gzip.compress(b"\n".join(json.dumps(c).encode() for c in cards))`.

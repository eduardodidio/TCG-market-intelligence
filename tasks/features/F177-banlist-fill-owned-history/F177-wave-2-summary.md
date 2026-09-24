# F177 — Wave 2 summary

**Status:** completed
**Tasks:** F177-T06, F177-T07, F177-T08
**Generated:** 2026-09-24T19:05:00Z

## Files touched
- `src/collectors/banlist_sync.py` (T06: rewrote bulk path — URL selection w/ redirects, gzip/JSONL/JSON-array parsing, set-code mapping, chunked upserts via legality_writer, fail-loud on 0 matches/0 lines)
- `tests/banlist/test_sync_f177.py` (T06: new fixtures/tests, `MockTransport`-based, no live network)
- `tests/banlist/test_sync.py` (T06: updated only assertions encoding old first-run-history behavior)
- `src/api/routers/banlist.py` (T07: `GET /banlist` switched to `banlist_queries.list_banlist_grouped` + `owned_only` optional-auth param; new `GET /banlist/status`)
- `src/api/schemas/banlist.py` (T07: `BanListEntry` gained `printings`/`owned`/`owned_quantity`; new `BanlistStatusSchema`)
- `tests/banlist/test_api_f177.py` (T07: new grouped/owned_only/status tests)
- `tests/banlist/test_api.py` (T07: updated for grouped response shape)
- `frontend/src/pages/BanList.tsx` (T08: "Somente minha coleção" toggle, `BanCardDetailModal` wiring, pagination, empty states; client-side sort removed)
- `frontend/src/api/banlist.ts` (T08: `ownedOnly` param, `fetchBanlistStatus()`)
- `frontend/src/types/banlist.ts` (T08: `BanListEntry` extended, new `BanlistStatus`)
- `frontend/tests/pages/BanList.test.tsx`, `frontend/tests/api/banlist.test.ts` (T08: updated mocks/assertions, `AuthProvider` wrapping)

## Decisions
- T06 kept the public `run_banlist_sync` signature and only added `scope: str = "compact"`, per Dev Notes — CLI and `POST /banlist/sync` call sites were left untouched.
- T08's task file header still reads `Status: planned` even though the implementation is present and tests updated — likely a missed status-flip by the developer; worth a TechLead check before sign-off.

## Notes for next Wave
- Wave 3 (T09/T10) touches `App.tsx`, `Layout.tsx`, `bats/`, `README.md` — none of those were touched in Wave 2, no conflict expected.
- `tests/banlist/` suite: 166 passed locally; the only pytest failure is the repo-wide 70% coverage gate (expected when running a subdirectory in isolation), not a real regression.
- Live Scryfall sync run (`bats\banlist-sync.bat`) is still pending-user per T06 notes — cloud sandbox can't reach Scryfall.

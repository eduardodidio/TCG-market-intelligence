# F177 — Wave 1 summary

**Status:** completed
**Tasks:** F177-T03, F177-T04, F177-T05
**Generated:** 2026-09-24T18:45:00Z

## Files touched
- `src/database/legality_writer.py` (T03: chunked multi-row upsert for `card_legalities` + `legality_history` via `dialect_insert`)
- `tests/banlist/test_legality_writer.py` (T03: happy/edge/boundary/error cases, temp-SQLite fixture)
- `src/database/banlist_queries.py` (T04: `list_banlist_grouped` + `get_banlist_status`, dialect-agnostic SQLAlchemy)
- `tests/banlist/test_banlist_queries.py` (T04: grouping, owned-filter, pagination, status-validation cases)
- `frontend/src/components/BanCardDetailModal.tsx` (T05: standalone modal, fetches legalities + ban history for one card)
- `frontend/tests/components/BanCardDetailModal.test.tsx` (T05: RTL + vitest, mocked `api/banlist`)

## Decisions
- T04 reads `printings/owned/owned_quantity` fields defensively via a local `ModalEntry` type since T08 (Wave 2) hasn't extended `BanListEntry` yet — avoids a forward dependency between T04/T05 and T08.
- Representative printing per group: owned printing wins, else lowest `card_id`; group status takes the most severe (banned > restricted) when printings disagree.

## Notes for next Wave
- Wave 2 (T06 sync rewrite, T07 API router, T08 frontend BanList) can now call `legality_writer.py` and `banlist_queries.py` directly — both are pure new modules, no edits to `repository.py`/`models.py` were made.
- T08 owns `api/banlist.ts` and `types/banlist.ts`; T05's modal already expects `fetchCardLegalities`/`fetchCardBanHistory` and a `ModalEntry`-shaped entry, so T08 should keep those signatures stable or update the modal's local type alongside its own changes.
- All three task files show `Status: done`; working tree still has these as untracked/modified — not yet committed as a Wave checkpoint.

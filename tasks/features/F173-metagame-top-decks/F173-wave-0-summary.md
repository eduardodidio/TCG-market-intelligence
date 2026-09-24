# F173 — Wave 0 summary

**Status:** completed
**Tasks:** F173-T01, F173-T02
**Generated:** 2026-09-24T18:10:00Z

## Files touched
- `docs/adr/0016-metagame-deck-sources.md` (T01: ADR Accepted — source matrix, EDHREC for Commander, MTGTop8 for the 6 constructed formats, live-verification flagged pending-user)
- `tests/fixtures/metagame/edhrec/**`, `tests/fixtures/metagame/mtgtop8/**` (T01: synthetic fixtures + per-source README with capture note)
- `src/metagame/__init__.py`, `src/metagame/sources/.gitkeep`, `tests/unit/metagame/__init__.py`, `frontend/src/components/meta/.gitkeep` (T01: scaffolding for Wave 1+)
- `docs/prd/F173-metagame-top-decks.md` (T02: PRD, status approved, all 9 ACs covered — 32 AC references found)

## Decisions
- Source per format locked in: `commander` → EDHREC (JSON, popularity-ranked, no meta share); `standard/pioneer/modern/legacy/vintage/pauper` → MTGTop8 (HTML + text decklist export, meta share %). No change needed to T08/README file names — plan already assumed MTGTop8.
- Live ToS/robots.txt verification could not run: the sandbox egress proxy returned 403 on CONNECT to all candidate hosts (edhrec.com, mtgtop8.com, mtggoldfish.com, mtgdecks.net). WebSearch only confirmed EDHREC's ToS URL and JSON endpoint existence. ADR marks verification **pending-user** and fixtures as **synthetic — revalidate on first real collection**.
- MTGGoldfish and mtgdecks.net dropped per the ToS-ban rule (both restrict automated scraping).

## Notes for next Wave
- Wave 1 (T03–T06) can proceed against the ADR's `SOURCE_FOR_FORMAT` mapping and the fixture files already in place; adapters (T07/T08 in Wave 2) must treat fixtures as synthetic until a human confirms robots.txt/ToS from a normal network — flag this in T07/T08 PRs, don't block on it.
- Backend tests must never hit the network (per README notes) — fixtures under `tests/fixtures/metagame/<source>/` are the only inputs for adapter tests.
- `src/metagame/sources/` currently only has `.gitkeep`; T04 creates the real `.py` files (base Protocol, `__init__.py` exports).

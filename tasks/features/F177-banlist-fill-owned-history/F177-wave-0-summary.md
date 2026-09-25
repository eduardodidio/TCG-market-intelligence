# F177 — Wave 0 summary

**Status:** completed
**Tasks:** F177-T01, F177-T02
**Generated:** 2026-09-24T18:21:24Z

## Files touched
- `docs/prd/F177-banlist-fill-owned-history.md` (T01: PRD covering diagnosis, AC1–AC12, rollout note)
- `docs/adr/0018-banlist-compact-legality-storage.md` (T01: compact storage + baseline history decision)
- `docs/diagrams/F177-architecture.mmd` (T01: sync → writer → card_legalities/legality_history → API → BanList/modal)
- `docs/diagrams/F177-journey.mmd` (T01: user flow incl. owned-only toggle, sync/empty states, `/banlist/history` redirect)
- `frontend/src/i18n/locales/en.json` (T02: added 16 `banlist.*` / `banlist.detail.*` keys)
- `frontend/src/i18n/locales/pt-BR.json` (T02: same keys, incl. `banlist.ownedOnly = "Somente minha coleção"`)
- `frontend/tests/i18n/banlist-f177-keys.test.tsx` (T02: new, asserts key parity + non-empty + pt-BR string)

## Decisions
- ADR 0018 fixed: compact legality storage (banned/restricted + owned + previously-existing rows only), first-run history seeded as `scryfall_baseline` rows only for banned/restricted cards.
- Branch confirmed as `wt/F177` (worktree branch merging into `homol`), not `main` — recorded in the PRD header.
- ADR number 0018 kept as reserved in `EXECUTION-PLAN-F171-F179.md`; not renumbered.

## Notes for next Wave
- `banlist.*` i18n keys (including nested `banlist.detail.*`) are now available in both locales — T05 (`BanCardDetailModal`) and T08 (`BanList.tsx`) can consume them directly without adding new keys.
- `nav.banHistory` / `banHistory.*` keys were intentionally left untouched (still used until T09 removes the page); do not delete them in later Waves before T09.
- Diagrams `F177-architecture.mmd` / `F177-journey.mmd` are the Wave-0 baseline; T10 re-syncs them at the end (sync-path details only) — don't hand-edit them in Waves 1–2, note gaps for T10 instead.
- `frontend/src/i18n/locales/*.json` is a shared hotspot across F171–F179 batch features — Wave 1/2 frontend tasks should re-check for upstream diffs before editing.
- Both new/updated i18n tests pass (`banlist-f177-keys.test.tsx`: 37 tests, `banHistory-keys.test.tsx`: 40 tests, all green). T01 made no code changes; pre-existing failures in `tests/unit/providers/liga/test_url.py`, `tests/unit/services/test_currency.py`, `tests/unit/test_liga_sweep_catalog.py` are unrelated/environmental (concurrent F171–F179 worktrees), not caused by Wave 0.

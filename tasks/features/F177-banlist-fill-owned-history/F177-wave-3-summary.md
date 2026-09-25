# F177 — Wave 3 summary

**Status:** completed
**Tasks:** F177-T09, F177-T10
**Generated:** 2026-09-24T20:30:00Z

## Files touched
- `frontend/src/App.tsx` (T09: `BanHistory` lazy import + route removed, `/banlist/history` now `<Navigate to="/banlist" replace />`)
- `frontend/src/components/Layout.tsx` (T09: "Histórico de banimentos" nav entry removed)
- `frontend/src/pages/BanHistory.tsx` (T09: deleted)
- `frontend/tests/pages/BanHistory.test.tsx` (T09: deleted)
- `frontend/tests/components/Layout.test.tsx`, `frontend/src/components/__tests__/Layout.test.tsx` (T09: nav item-count assertions updated for the removed link)
- `frontend/tests/pages/F97-breadcrumbs.test.tsx` (T09: dropped its `BanHistory` breadcrumb test, not anticipated in the task's Dev Notes)
- `frontend/tests/routes/banlistRedirect.test.tsx` (T09: new — asserts `/banlist/history` redirects and renders `page-banlist`)
- `bats/banlist-sync.bat` (T10: new — runs `python -m src.cli.main banlist-sync`, exits 1 on `errorlevel`)
- `README.md` (T10: new "F177 -- Ban List" section covering sync fix, `.bat`, API, frontend, routing)
- `tests/banlist/test_bats.py` (T10: new static guard for the `.bat` file)

## Decisions
- T10 found no drift between `docs/diagrams/F177-architecture.mmd` / `F177-journey.mmd` (already correct from Wave 0) and the merged Wave 1/2 code, so no diagram edits were needed this wave.
- T09 widened its diff slightly beyond the two hotspot files (`F97-breadcrumbs.test.tsx`, both `Layout.test.tsx` copies) because those suites hardcoded the beta-nav item count / referenced `BanHistory` directly.

## Notes for next Wave
- All Wave 3 changes are still uncommitted in the working tree (no "F177 Wave 3" commit yet) — TechLead/QA should review the working tree, not just `git log`.
- `F177-T10.md`'s own header still says `Status: planned` even though its deliverables (bat, README, test) are all present — worth correcting before final sign-off.
- Developer's T09 notes call out several **pre-existing, unrelated** test failures (UpdatePrompt, OfflineBanner, TreasureModal, Login OAuth, MyCollection, MyTrades, ImportPurchasesPage, 2 Layout nav-count assertions) confirmed via `git stash` to predate this task — do not attribute these to F177 in review.

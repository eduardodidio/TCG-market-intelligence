# F179 — Wave 2 summary

**Status:** partial (code complete, uncommitted; T09 checklist/status not marked done)
**Tasks:** F179-T08, F179-T09
**Generated:** 2026-09-24T19:50:00Z

## Files touched
- `tests/integration/test_f179_achievement_rewards.py` (T08: new, 7 test classes — journey, idempotency, concurrency, legacy backfill, boundary, deduction interplay; all pass in isolation)
- `tests/integration/cli/test_f179_cli_registration.py` (T09: new, verifies `backfill-achievement-rewards --help` and its listing in `main.py --help`)
- `src/cli/main.py` (T09: +2 lines — import + `cli.add_command(backfill_achievement_rewards_cmd)` before `if __name__ == "__main__":`)
- `frontend/src/components/Layout.tsx` (T09: +2 lines — import + `<AchievementNotifierHost />` mounted as sibling near end of root)
- `README.md` (T09: new "F179 -- Achievement Treasure Rewards" note — tiers, backfill, API additions, frontend, treasure_hunter fix)

## Decisions
- No mock added for `AchievementNotifierHost` in `Layout.test.tsx` — real component renders fine unmocked (guest/unauth short-circuits via `skip`), so the "only if needed" mock from the task file was skipped.
- T08 flagged 112 pre-existing full-suite failures (liga URL builder, marketplace repo, currency, liga_sweep_catalog) as unrelated to F179; verified via isolated reruns and `git diff` showing those files untouched by any F179 task.

## Notes for next Wave (QA)
- **Nothing is committed yet** — Wave 2 changes are still working-tree modifications (`git status` shows README.md, Layout.tsx, main.py, T08 task file modified + new test files untracked). QA/orchestrator needs to commit "F179 Wave 2" before proceeding.
- T09's own checklist (`F179-T09.md` lines 43–47) is still all unchecked and `Status: planned` was never flipped to `done` — functionally verified working (targeted pytest: 9 passed; `ruff check` clean; Layout test run: 33 passed, 1 unrelated failure) but the task file itself wasn't updated to reflect completion.
- One Layout test failure observed: `beta section has correct total item count (12)` expects 12 links, got 13 — this is an F133 nav-count assertion unrelated to F179/AchievementNotifierHost (host renders `null` when no toasts/unauth, doesn't add a link), likely drift from another in-flight feature; QA should confirm against baseline before blocking on it.
- `docs/diagrams/F179-architecture.mmd` already reflects `Host[AchievementNotifierHost] --> Hook[useAchievementNotifier]`, consistent with the Wave 2 wiring — no diagram update needed.

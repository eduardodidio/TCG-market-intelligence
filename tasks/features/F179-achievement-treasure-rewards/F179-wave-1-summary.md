# F179 — Wave 1 summary

**Status:** completed
**Tasks:** F179-T04, F179-T05, F179-T06, F179-T07
**Generated:** 2026-09-24T21:00:00Z

## Files touched
- `src/services/achievements.py` (T04: credit-on-unlock via `check_achievements_with_rewards()`, lazy backfill, `_get_user_stats` bonus-reason fix for `treasure_hunter`)
- `src/api/routers/achievements.py` (T04: `GET /achievements` items add `reward`/`tier`/`reward_credited`; `POST /achievements/check` adds `rewards`, `total_reward`, `backfilled`, `balance`)
- `tests/services/test_achievements.py`, `tests/api/test_achievements_router.py` (T04: coverage for idempotent crediting, backfill, bonus-reason fix)
- `src/cli/achievement_rewards.py` (T05, new: `backfill-achievement-rewards` command with `--dry-run`; not yet registered — that's T09)
- `tests/integration/cli/test_achievement_rewards_cli.py` (T05, new)
- `frontend/src/pages/AchievementsPage.tsx` (T06: reward chip + tier per card, "X / Y Tesouros ganhos" progress)
- `frontend/src/pages/__tests__/AchievementsPage.test.tsx` (T06)
- `frontend/src/components/AchievementToast.tsx`, `frontend/src/hooks/useAchievementNotifier.ts` (T07: reward toast text, handles `backfilled > 0` even when `newly_unlocked` is empty, 30s throttle, calls `notifyCreditsChanged()`)
- `frontend/src/components/AchievementNotifierHost.tsx` (T07, new: still unmounted — Wave 2's T09 mounts it in `Layout.tsx`)
- `frontend/src/components/__tests__/AchievementToast.test.tsx`, `frontend/src/hooks/__tests__/useAchievementNotifier.test.ts`, `frontend/src/components/__tests__/AchievementNotifierHost.test.tsx` (T07)

All four task files (`F179-T04.md`…`F179-T07.md`) marked `Status: done`. Changes are uncommitted in the worktree (no Wave 1 commit yet — Wave 0 committed as `d1fbd49`).

## Decisions
- T04 fixed the `treasure_hunter` bug by counting both `"bonus"` and `"bonus_claim"` transaction reasons (`claim_bonus` in `src/credits/service.py` actually writes `"bonus_claim"`), per AC8.
- T04 kept `check_achievements(user_id, repo) -> list[str]` unchanged for backward compat; the richer reward data comes from the new `check_achievements_with_rewards()`.
- T06 defensively treats `reward`/`tier` as optional (`reward ?? 0`, hide chip if 0) since it ran in parallel with T04 and couldn't assume backend fields existed yet.

## Notes for next Wave
- T05's `src/cli/achievement_rewards.py` is written but **not yet wired into `src/cli/main.py`** — T09 (Wave 2) must add the 2-line registration.
- T07's `AchievementNotifierHost.tsx` exists but is **not mounted anywhere** — T09 must mount it in `Layout.tsx` for toasts to actually appear app-wide (AC7 depends on this).
- `frontend/src/components/__tests__/Layout.test.tsx` will need a mock for the new host once T09 mounts it.
- Nothing from Wave 1 has been committed yet; Wave 2 (T08 integration test, T09 shared wiring) will need to account for all these uncommitted changes together.

DIDIO_DONE: techlead wrote F179-wave-1-summary.md

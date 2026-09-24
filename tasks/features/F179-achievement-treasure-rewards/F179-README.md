# F179 — Conquistas recompensam tokens de Tesouro

**Status:** planned

## Goal

Every achievement (F109) now pays out Treasure tokens (F65 credit system),
scaled by difficulty through five MTG-rarity tiers — Comum 50, Incomum 100,
Rara 250, Mítica 500, Lendária 1000. The reward is credited exactly once per
user/achievement and recorded in the `credit_transactions` ledger
(`reason="achievement_reward"`, `reference_id="achievement:<key>"`).
Achievements unlocked before this feature are backfilled, both lazily (on
the next `/achievements/check`) and via a one-off CLI command. The reward shows
on the Achievements page (per card + earned/total) and in the unlock toast.
The toast is currently not mounted anywhere, so this feature also mounts it app-wide.
Also fixes a latent bug where `treasure_hunter` could never unlock.

Brief (sharded): `_brief/00-overview.md` … `_brief/05-shared-wiring.md`.

## Architecture Impact

- **Backend service (new):** `src/services/achievement_rewards.py`: tier
  table, mapping, idempotent in-session crediting, backfill.
- **Backend service (modified):** `src/services/achievements.py`: credit on
  unlock (same transaction), lazy backfill, reward fields, bonus-reason fix.
- **API (modified):** `src/api/routers/achievements.py`: reward fields, `/check`
  returns rewards + balance. No new router, no `app.py` change.
- **CLI (new module):** `src/cli/achievement_rewards.py`, registered with 2 lines in `main.py`.
- **Frontend:** types, i18n, `useCredits` refresh event, AchievementsPage,
  AchievementToast, useAchievementNotifier, new `AchievementNotifierHost`
  (mounted in `Layout.tsx` by the last-Wave task).
- **DB:** no schema change, no migration (reuses ledger tables).

## Waves

- **Wave 0**: F179-T01, F179-T02, F179-T03
- **Wave 1**: F179-T04, F179-T05, F179-T06, F179-T07
- **Wave 2**: F179-T08, F179-T09

## Files touched per task (for cross-feature overlap detection)

| Task | Wave | Files (N = new) |
|------|------|-----------------|
| T01 docs | 0 | `docs/prd/F179-achievement-treasure-rewards.md` (N), `docs/adr/<next>-achievement-reward-ledger-idempotency.md` (N), `docs/diagrams/F179-architecture.mmd` (N), `docs/diagrams/F179-journey.mmd` (N) |
| T02 backend | 0 | `src/services/achievement_rewards.py` (N), `tests/services/test_achievement_rewards.py` (N) |
| T03 frontend | 0 | `frontend/src/types/achievements.ts`, `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt-BR.json`, `frontend/src/utils/creditsEvents.ts` (N), `frontend/src/hooks/useCredits.ts`, `frontend/src/hooks/__tests__/useCredits.test.ts` (N or extend), `frontend/src/utils/__tests__/creditsEvents.test.ts` (N) |
| T04 backend | 1 | `src/services/achievements.py`, `src/api/routers/achievements.py`, `tests/services/test_achievements.py`, `tests/api/test_achievements_router.py` |
| T05 backend CLI | 1 | `src/cli/achievement_rewards.py` (N), `tests/integration/cli/test_achievement_rewards_cli.py` (N) |
| T06 frontend | 1 | `frontend/src/pages/AchievementsPage.tsx`, `frontend/src/pages/__tests__/AchievementsPage.test.tsx` |
| T07 frontend | 1 | `frontend/src/components/AchievementToast.tsx`, `frontend/src/hooks/useAchievementNotifier.ts`, `frontend/src/components/AchievementNotifierHost.tsx` (N), tests: `components/__tests__/AchievementToast.test.tsx`, `hooks/__tests__/useAchievementNotifier.test.ts`, `components/__tests__/AchievementNotifierHost.test.tsx` (N) |
| T08 test | 2 | `tests/integration/test_f179_achievement_rewards.py` (N) |
| T09 shared wiring | 2 | **HIGH-RISK SHARED:** `src/cli/main.py` (+2 lines), `frontend/src/components/Layout.tsx` (+2 lines), `README.md` (+note); `frontend/src/components/__tests__/Layout.test.tsx` (mock only if needed) |

Shared-file notes for the batch orchestrator:
- Only T09 touches batch-shared files (`main.py`, `Layout.tsx`, `README.md`).
  It does NOT touch `App.tsx`, `models.py`, `app.py`, or `bats/`.
- i18n JSON files (T03) are edited additively inside the existing
  `"achievements"` object only. Other features adding their own sections
  should merge cleanly.
- ADR number: T01 picks the next free number when it writes the file.
  F173/F176 also add ADRs in this batch, so if two collide at merge time,
  renumber this one.

## Patterns

- **Crediting in the same transaction as the unlock:** the `AchievementRow`
  unique constraint is the serialization point (`rowcount == 1` → credit).
- **Backfill** checks the ledger for an existing row under a
  `with_for_update()` lock on the balance row.
- Rewards are permanent (no revocation).
- `check_achievements()` keeps its `list[str]` return for backward compat.
  The richer result comes from `check_achievements_with_rewards()`.

## Global Acceptance Criteria

1. Tier table 50/100/250/500/1000, and all 11 achievements mapped (test fails if a new definition is unmapped).
2. Unlocking an achievement credits its reward once. Balance and ledger (`achievement_reward`, `achievement:<key>`) are consistent.
3. Repeated or concurrent `/achievements/check` calls never double-credit, and `newly_unlocked` has no duplicates.
4. Achievements unlocked before F179 get credited exactly once, lazily on `/check` and via `backfill-achievement-rewards` (`--dry-run` writes nothing). Re-running is a no-op.
5. `GET /achievements` items include `reward`, `tier`, `reward_credited`. `POST /achievements/check` returns `rewards`, `total_reward`, `backfilled`, `balance` and keeps `newly_unlocked`.
6. AchievementsPage shows the reward chip and tier on every card, plus "X / Y Tesouros ganhos".
7. Toast shows "+N Tesouros adicionados!". Toasts appear app-wide for authenticated non-guest users, and TreasureBalance refreshes without a reload.
8. `treasure_hunter` unlocks after 5 `bonus_claim` transactions.
9. Works on SQLite and PostgreSQL. `ruff check src/`, `pytest tests/`, `cd frontend && npm test` and `npm run build` all pass.
10. PRD, ADR, `F179-architecture.mmd`, `F179-journey.mmd` and the README note are delivered.

## Diagrams

- `docs/diagrams/F179-architecture.mmd` (owner T01)
- `docs/diagrams/F179-journey.mmd` (owner T01)

## Test Impact (existing tests that may need updates)

- `tests/services/test_achievements.py`: the treasure_hunter test may seed
  `reason="bonus"`. Keep it passing, since both reasons count.
- `tests/api/test_achievements_router.py`: `/check` payload grows (additive).
- `frontend/src/hooks/__tests__/useAchievementNotifier.test.ts`,
  `components/__tests__/AchievementToast.test.tsx`,
  `pages/__tests__/AchievementsPage.test.tsx`: mocks need the new optional fields.
- `frontend/src/components/__tests__/Layout.test.tsx`: mock the new host (T09).
- `frontend/src/components/__tests__/TreasureBalance.test.tsx`: `useCredits` gains a listener. Verify it still passes.

## Setup / Gitflow (Wave 0 checklist)

- Work on the branch/worktree assigned by the batch orchestrator. It merges
  into `homol`, never directly into `main`.
- Stage files one by one. No new dependencies. No `.claude/settings.json`
  changes are needed (only pytest, ruff and npm test/build).

## ADR number (batch reservation)
This feature's ADR number is **0020**, reserved in `tasks/features/EXECUTION-PLAN-F171-F179.md`. It overrides any "next free number" instruction in the task files.

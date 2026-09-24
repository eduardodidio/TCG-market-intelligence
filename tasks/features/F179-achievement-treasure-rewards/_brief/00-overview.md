# F179 — Overview: Conquistas recompensam tokens de Tesouro

## Problem

Achievements (F109) already unlock (`src/services/achievements.py`,
`src/api/routers/achievements.py`, `AchievementsPage.tsx`,
`AchievementToast.tsx`, `useAchievementNotifier.ts`), but they give nothing
back. The platform has a Treasure token economy (F65: `src/credits/`,
`credit_balances` + `credit_transactions` ledger, `TreasureBalance.tsx`).
Each achievement must now credit Treasure tokens once per user, scaled by
difficulty (50 → 1000), be recorded in the ledger, be backfilled for
achievements that were unlocked before this feature, and be shown on the
Achievements page and in the unlock toast.

## Scope

- Reward tier table (5 tiers) + per-achievement tier mapping — pure module.
- Idempotent crediting: exactly one ledger row per (user, achievement).
- Hook crediting into `check_achievements` and `grant_set_master`.
- Backfill: lazy (per user, on `/achievements/check`) + CLI command for all users.
- API: expose `reward`/`tier`/`reward_credited` per achievement; `/check`
  returns rewards credited + new balance.
- Frontend: reward badge + totals on AchievementsPage; reward line in toast;
  mount the (currently unmounted!) notifier so toasts actually appear;
  Treasure balance refresh after a reward.
- Fix latent bug: `treasure_hunter` counts `reason == "bonus"` but
  `CreditService.claim_bonus` writes `reason="bonus_claim"` — it can never unlock.

## Out of scope

- New achievements; wiring `grant_set_master` into set-completion (it is
  currently not called anywhere — only make it credit when it is called).
- Schema changes / migrations (none needed — see `01-reward-model.md`).
- Reward revocation if a user later drops below a threshold (rewards are permanent).

## Constraints

- No new dependencies. No `models.py` / migration changes.
- Must work on SQLite (tests/local) and Neon PostgreSQL (prod).
- Batch F171–F178 runs in parallel: high-risk shared files
  (`frontend/src/App.tsx`, `frontend/src/components/Layout.tsx`,
  `src/cli/main.py`, `src/database/models.py`, `src/api/app.py`, `README.md`,
  `bats/`) are touched ONLY by F179-T09 (last Wave), with 1–3 line edits.
- Gitflow: work on the worktree/branch assigned by the orchestrator, merged
  into `homol`. Never commit/push to `main`.
- Stage files one by one (never `git add -A` / `git add .`).

## Global Acceptance Criteria (titles)

- AC1 Tier table 50/100/250/500/1000 and every achievement mapped to a tier
- AC2 One-time credit per (user, achievement), recorded in ledger
- AC3 Concurrent/duplicate `/check` calls never double-credit
- AC4 Backfill credits previously-unlocked achievements exactly once (lazy + CLI)
- AC5 API exposes reward info; `/check` returns credited rewards + balance
- AC6 AchievementsPage shows reward per card + earned/total treasure
- AC7 Toast shows "+N Tesouros" and Treasure balance refreshes
- AC8 `treasure_hunter` becomes reachable (counts `bonus_claim`)
- AC9 PRD, ADR, two diagrams, README note delivered

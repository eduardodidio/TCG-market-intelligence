# PRD: Conquistas recompensam tokens de Tesouro

**Feature ID:** F179
**Status:** in-progress
**Owner:** @eduardodidio
**Date:** 2026-09-24

## Problem

Achievements (F109) already unlock and are shown on the Achievements page
and in an unlock toast, but unlocking one gives the player nothing back.
The platform already has a Treasure token economy (F65: `credit_balances`
+ `credit_transactions` ledger, `TreasureBalance.tsx`), but achievements
and Treasure are disconnected. Players who complete achievements have no
tangible in-app reward, and one achievement (`treasure_hunter`) can never
unlock at all because of a latent reason-string mismatch.

## Goal

Every achievement pays out Treasure tokens exactly once per user, scaled
by difficulty across five MTG-rarity tiers, recorded durably in the
existing credit ledger, backfilled for players who unlocked achievements
before this feature shipped, and visible on the Achievements page and in
the unlock toast.

## Scope

### In scope

- Reward tier table (5 tiers) and a per-achievement tier mapping covering
  all 11 current achievement keys.
- Idempotent crediting: exactly one `credit_transactions` row per
  `(user_id, achievement_key)`, using the ledger itself (no new unique
  index) as the idempotency guard.
- Crediting hooked into `check_achievements` (unlock path) and
  `grant_set_master`.
- Backfill for achievements unlocked before F179: lazy, on the next
  `/achievements/check`, plus a one-off CLI command
  (`backfill-achievement-rewards`, with `--dry-run` and `--user-id`).
- API: `GET /achievements` items expose `reward`, `tier`,
  `reward_credited`; `POST /achievements/check` additionally returns
  `rewards`, `total_reward`, `backfilled`, `balance` (keeps
  `newly_unlocked` for backward compat).
- Frontend: reward chip + tier per card and an earned/total Tesouros
  summary on the Achievements page; reward line in the unlock toast;
  mounting the (currently unmounted) toast notifier app-wide via a new
  `AchievementNotifierHost` in `Layout.tsx`; Treasure balance
  (`useCredits`) refreshes without a page reload after a reward.
- Fix: `treasure_hunter` currently counts transactions with
  `reason == "bonus"`, but `CreditService.claim_bonus` writes
  `reason="bonus_claim"`, so it can never unlock. Fixed to count
  `bonus_claim`.

### Out of scope

- New achievements, or wiring `grant_set_master` into set-completion
  flows (it is not currently called anywhere; this feature only makes it
  credit correctly when it is called).
- Any schema change or migration (the ledger tables already have every
  column needed).
- Reward revocation if a user later drops below a threshold — rewards
  are permanent once credited.

## Tier table and mapping

| Tier key    | Tesouros | Label pt-BR | Label en  |
|-------------|---------:|-------------|-----------|
| `common`    |       50 | Comum       | Common    |
| `uncommon`  |      100 | Incomum     | Uncommon  |
| `rare`      |      250 | Rara        | Rare      |
| `mythic`    |      500 | Mítica      | Mythic    |
| `legendary` |     1000 | Lendária    | Legendary |

| achievement_key   | tier        | reward |
|-------------------|-------------|-------:|
| `first_card`      | common      |     50 |
| `deck_builder`    | common      |     50 |
| `scanner`         | common      |     50 |
| `price_watcher`   | common      |     50 |
| `collector_10`    | uncommon    |    100 |
| `early_adopter`   | uncommon    |    100 |
| `collector_50`    | rare        |    250 |
| `treasure_hunter` | rare        |    250 |
| `collector_100`   | mythic      |    500 |
| `collector_500`   | legendary   |   1000 |
| `set_master`      | legendary   |   1000 |

An unmapped/unknown key returns reward `0` / tier `None` and nothing is
credited (defensive default); a test asserts every key in
`ACHIEVEMENT_DEFINITIONS` has a tier mapping.

## User flows

See `docs/diagrams/F179-architecture.mmd` (component/data-flow) and
`docs/diagrams/F179-journey.mmd` (user journey, including the backfill
and error branches).

## Success metrics

- **AC1** — Tier table 50/100/250/500/1000, and all 11 achievements
  mapped (test fails if a new definition is unmapped).
- **AC2** — Unlocking an achievement credits its reward once. Balance and
  ledger (`achievement_reward`, `achievement:<key>`) are consistent.
- **AC3** — Repeated or concurrent `/achievements/check` calls never
  double-credit, and `newly_unlocked` has no duplicates.
- **AC4** — Achievements unlocked before F179 get credited exactly once,
  lazily on `/check` and via `backfill-achievement-rewards`
  (`--dry-run` writes nothing). Re-running is a no-op.
- **AC5** — `GET /achievements` items include `reward`, `tier`,
  `reward_credited`. `POST /achievements/check` returns `rewards`,
  `total_reward`, `backfilled`, `balance` and keeps `newly_unlocked`.
- **AC6** — AchievementsPage shows the reward chip and tier on every
  card, plus "X / Y Tesouros ganhos".
- **AC7** — Toast shows "+N Tesouros adicionados!". Toasts appear
  app-wide for authenticated non-guest users, and TreasureBalance
  refreshes without a reload.
- **AC8** — `treasure_hunter` unlocks after 5 `bonus_claim` transactions.
- **AC9** — Works on SQLite and PostgreSQL. `ruff check src/`,
  `pytest tests/`, `cd frontend && npm test` and `npm run build` all
  pass.
- **AC10** — PRD, ADR, `F179-architecture.mmd`, `F179-journey.mmd` and
  the README note are delivered.
- **Metric:** total Tesouros granted via `achievement_reward`
  (`SUM(amount) FROM credit_transactions WHERE reason = 'achievement_reward'`)
  is observable and non-zero after backfill + normal usage.

## Open questions

- None outstanding for this batch. A future feature may add a partial
  unique index on `(user_id, reason, reference_id)` — see
  `docs/adr/0020-achievement-reward-ledger-idempotency.md` §Consequences.

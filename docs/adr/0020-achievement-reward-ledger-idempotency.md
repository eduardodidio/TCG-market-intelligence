# ADR-0020: Achievement Reward Ledger Idempotency

## Status
Accepted

## Context
F179 makes every achievement pay out Treasure tokens (F65 credit system)
through the existing `credit_balances` / `credit_transactions` ledger
(`src/database/models.py`). The reward must be credited exactly once per
`(user_id, achievement_key)`, both on the unlock path (`check_achievements`)
and on the backfill path (achievements unlocked before this feature).

The natural idempotency key is `(user_id, reason, reference_id)` on
`credit_transactions`, but there is no unique index on it — adding one
would require a `models.py` change and a migration. This batch (F171–F179)
explicitly forbids `models.py` changes to keep the parallel Waves
conflict-free, so idempotency has to be guaranteed by transaction ordering
and explicit existence checks instead of a database constraint.

## Decision
1. **Unlock path is the primary serialization point.** `AchievementRow`
   already has a unique constraint (`uq_user_achievement`). The unlock
   insert uses `on_conflict_do_nothing`; the reward is credited only when
   `result.rowcount == 1`, in the SAME SQLAlchemy session/transaction as
   the achievement insert. A concurrent duplicate unlock gets `rowcount
   == 0` and is never credited.
2. **Backfill path serializes through a row lock, not a unique index.**
   `backfill_user_rewards_in_session` locks the user's `CreditBalanceRow`
   with `.with_for_update()` (no-op on SQLite, a real row lock on
   PostgreSQL/Neon) before checking whether a ledger row for that
   idempotency key already exists. Two concurrent backfills for the same
   user therefore serialize on that lock instead of racing on an insert.
3. **The unlock path also performs the existence check** (belt and
   braces) before crediting, so an unlock that lands after a
   partially-applied backfill never double-credits.
4. **Reason/reference_id convention:** `reason = "achievement_reward"`
   (constant `ACHIEVEMENT_REWARD_REASON`), `reference_id =
   "achievement:<achievement_key>"`. Both fit within the existing column
   lengths, so no schema change is needed.

## Consequences
- No migration, no `models.py` edit — safe to land inside a batch that
  freezes shared schema files.
- Idempotency is enforced in application code (existence check + row
  lock), not by the database, so it depends on all reward-crediting code
  paths going through `credit_reward_in_session` / the backfill helpers —
  any new caller that writes `credit_transactions` directly for this
  reason would bypass the guarantee.
- **Future improvement:** add an optional partial unique index on
  `(user_id, reason, reference_id)` in `credit_transactions` (e.g. a
  Postgres partial index scoped to `reason = 'achievement_reward'`) as a
  belt-and-braces database-level guarantee once a schema-change window is
  available. Not required for correctness today because of points 1–3
  above.

## Alternatives considered
- **New column `reward_credited_at` on the achievements table.** Rejected:
  requires a `models.py` change and a migration, which this batch
  explicitly forbids to avoid conflicts with the other parallel F171–F178
  features touching shared schema files. The ledger-based approach reuses
  tables that already exist and need no migration.

# 01 — Reward model (tiers, mapping, ledger contract)

## Tiers (MTG-rarity themed)

| Tier key    | Tesouros | Label pt-BR | Label en  |
|-------------|---------:|-------------|-----------|
| `common`    |       50 | Comum       | Common    |
| `uncommon`  |      100 | Incomum     | Uncommon  |
| `rare`      |      250 | Rara        | Rare      |
| `mythic`    |      500 | Mítica      | Mythic    |
| `legendary` |     1000 | Lendária    | Legendary |

## Mapping (all 11 current achievements)

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

Unknown key → `get_reward()` returns 0 / tier `None` and nothing is credited
(defensive; a test asserts every key in `ACHIEVEMENT_DEFINITIONS` is mapped).

## Ledger contract (no schema change)

Reuse `credit_transactions` (`CreditTransactionRow`) and `credit_balances`
(`CreditBalanceRow`) from `src/database/models.py`:

- `reason = "achievement_reward"` (constant `ACHIEVEMENT_REWARD_REASON`, ≤ 50 chars)
- `reference_id = "achievement:<achievement_key>"` (≤ 200 chars)
- `amount = +reward`

Idempotency key = `(user_id, reason, reference_id)`. There is no DB unique
index on it (adding one would need `models.py` + migration — forbidden in this
batch), so idempotency is guaranteed by:

1. **Unlock path:** credit only when the `AchievementRow` insert actually
   inserted a row (`on_conflict_do_nothing` + `result.rowcount == 1`), in the
   SAME SQLAlchemy session/transaction as the insert. The unique constraint
   `uq_user_achievement` makes the insert the serialization point: a
   concurrent duplicate gets rowcount 0 → no credit.
2. **Backfill path:** credit only when no ledger row with that idempotency key
   exists. Lock the user's `CreditBalanceRow` with `.with_for_update()`
   (no-op on SQLite, row lock on Postgres) before the existence check, so two
   concurrent backfills for the same user serialize.
3. Unlock path also performs the existence check (belt and braces), so an
   unlock after a partially-applied backfill never double-credits.

## Crediting inside a session

`Repository.update_credit_balance` opens its own session, so it cannot share
the achievement insert's transaction. The new module writes rows directly:

```python
def credit_reward_in_session(session: Session, user_id: int, key: str) -> int:
    amount = get_reward(key)
    if amount <= 0:
        return 0
    ref = f"achievement:{key}"
    bal = session.execute(
        select(CreditBalanceRow).where(CreditBalanceRow.user_id == user_id).with_for_update()
    ).scalar_one_or_none()
    if bal is None:
        bal = CreditBalanceRow(user_id=user_id, balance=0)
        session.add(bal)
        session.flush()
    exists = session.execute(
        select(CreditTransactionRow.id).where(
            CreditTransactionRow.user_id == user_id,
            CreditTransactionRow.reason == ACHIEVEMENT_REWARD_REASON,
            CreditTransactionRow.reference_id == ref,
        ).limit(1)
    ).first()
    if exists:
        return 0
    bal.balance += amount
    session.add(CreditTransactionRow(user_id=user_id, amount=amount,
                                     reason=ACHIEVEMENT_REWARD_REASON, reference_id=ref))
    return amount
```

Caller commits. Check `CreditBalanceRow` field names in `models.py` before
coding (`user_id`, `balance`, `last_bonus_at`, `last_monthly_grant_at`).

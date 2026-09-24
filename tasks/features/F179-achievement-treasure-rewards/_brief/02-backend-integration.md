# 02 — Backend integration (achievements service + router)

## `src/services/achievements.py` changes

1. `check_achievements(user_id, repo)`:
   - Keep signature and return type (`list[str]` newly unlocked) for backward
     compat; add a sibling `check_achievements_with_rewards(user_id, repo) -> dict`
     returning `{"newly_unlocked": [...], "rewards": [{"key", "amount", "tier"}],
     "total_reward": int, "backfilled": int}`; `check_achievements` delegates and
     returns `result["newly_unlocked"]`.
   - Append to `newly_unlocked` ONLY when `result.rowcount == 1` (today it appends
     unconditionally → race shows duplicate toasts).
   - For each newly inserted row call `credit_reward_in_session(session, user_id, key)`
     in the same session, then a single `session.commit()`.
   - After that, call `backfill_user_rewards_in_session(session, user_id)` to
     credit any unlocked-but-unrewarded achievements (lazy backfill); sum into
     `backfilled`. Commit once.
   - The current early return `if not earned_keys: return []` must be removed/moved:
     the lazy backfill runs even when nothing is earned now (e.g. a user whose
     only achievement is a previously granted `set_master`).
2. `grant_set_master(user_id, repo)`: when rowcount == 1, credit reward in the
   same session before commit.
3. `get_user_achievements(user_id, repo)`: each item gains
   `reward: int`, `tier: str | None`, `reward_credited: bool` (true when a ledger
   row with `reference_id="achievement:<key>"` exists — one query for all keys).
4. Bug fix in `_get_user_stats`: bonus claims must count
   `CreditTransactionRow.reason.in_(("bonus", "bonus_claim"))` (claim_bonus writes
   `"bonus_claim"`, see `src/credits/service.py`). Never count
   `achievement_reward`.

## `src/api/routers/achievements.py`

- `GET /api/v1/achievements` → each item adds `reward`, `tier`, `reward_credited`.
  Keep the response a list (frontend expects `AchievementItem[]`); totals are
  computed client-side.
- `POST /api/v1/achievements/check` → `data`:
  ```json
  {"newly_unlocked": ["first_card"],
   "rewards": [{"key": "first_card", "amount": 50, "tier": "common"}],
   "total_reward": 50,
   "backfilled": 0,
   "balance": 1234}
  ```
  `balance` via `CreditService(repo).get_balance(user.id).balance`.
  `newly_unlocked` stays for backward compatibility.

## Tests

- `tests/services/test_achievements.py` — extend (existing fixtures: tmp sqlite
  `Repository`, `repo.create_user`).
- `tests/api/test_achievements_router.py` — extend (FastAPI app with
  `dependency_overrides[get_db]`/`[get_current_user]`).

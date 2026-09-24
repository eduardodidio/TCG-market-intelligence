# 03 — Backfill

Two paths, same core function from `src/services/achievement_rewards.py`:

- `backfill_user_rewards_in_session(session, user_id) -> int` — for every
  `AchievementRow` of the user, `credit_reward_in_session(...)`; returns total
  credited. Caller commits.
- `backfill_all_rewards(repo, *, dry_run=False, user_id=None) -> dict` —
  iterates distinct `AchievementRow.user_id` (or just `user_id`), one session +
  commit per user (a failure on one user is logged via structlog and does not
  abort the others). Returns
  `{"users": n, "credited_users": n, "credited_rows": n, "total_tokens": n,
  "errors": n}`. `dry_run=True` computes what would be credited and rolls back.

## Lazy path

Called from `check_achievements_with_rewards` (see `02-backend-integration.md`),
so any user that opens the app (the notifier calls `/check`) is backfilled
automatically — no manual prod step is strictly required.

## CLI path (new file, registered by T09)

`src/cli/achievement_rewards.py`:

```python
import click

@click.command("backfill-achievement-rewards")
@click.option("--db", default=None, callback=_resolve_db, is_eager=True, expose_value=True,
              help="Database URL (default: auto-detect)")
@click.option("--dry-run", is_flag=True, help="Show what would be credited without writing")
@click.option("--user-id", type=int, default=None, help="Only backfill this user")
def backfill_achievement_rewards_cmd(db, dry_run, user_id):
    """Credit Treasure rewards for achievements unlocked before F179."""
```

Prints a summary line like
`Backfill complete: 12 users, 31 rewards, 4850 Tesouros credited (dry-run: no)`.

IMPORTANT (import cycle): `src/cli/main.py` will do
`cli.add_command(backfill_achievement_rewards_cmd)` importing from this module.
Do NOT import `src.cli.main` at module top level in `achievement_rewards.py`;
define a local copy of main.py's callback:

```python
def _resolve_db(ctx, param, value):
    if value is None:
        from src.config import get_db_url
        return get_db_url()
    return value
```

Registration line (done by T09 only):
```python
from src.cli.achievement_rewards import backfill_achievement_rewards_cmd  # noqa: E402
cli.add_command(backfill_achievement_rewards_cmd)
```
placed right before `if __name__ == "__main__":`.

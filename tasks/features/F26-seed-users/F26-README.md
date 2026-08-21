# F26 — Seed Users

**Status:** planned
**Depends on:** F22 (authentication)

## Summary

Create a CLI command `seed-users` that provisions two initial users with
bcrypt-hashed passwords. The command is idempotent — skips users that
already exist by email.

Users to create:
1. `eduardo.didio` (email: eduardo.didio) — password: mudar@123
2. `anderson.serafim` (email: anderson.serafim) — password: mudar@123

## Architecture Impact

- `src/cli/main.py` — new `seed-users` CLI command
- `src/database/repository.py` — uses existing `create_user` + `get_user_by_email`
- `src/auth/passwords.py` — uses existing `hash_password`

No new models, no new API endpoints, no frontend changes.

## Wave Manifest

| Wave | Tasks | Description                          |
|------|-------|--------------------------------------|
| 0    | T01   | CLI seed-users command + tests       |

## Global Acceptance Criteria

- [ ] `python -m src.cli.main seed-users` creates both users
- [ ] Running twice does not fail or duplicate users
- [ ] Passwords work with existing login flow
- [ ] Tests cover idempotent behavior

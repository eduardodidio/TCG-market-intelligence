# T02 -- Reset Password CLI Command

**Wave:** 0
**Depends on:** none
**Estimated effort:** small

## User Story

As an admin, I want to reset a user's password from the command line so
that I can help users who forgot their credentials without needing an
email service.

## What to Build

Add a `reset-password` CLI command to `src/cli/main.py`:

```
tcg reset-password --email user@example.com [--password <custom>] [--expires-hours 24]
```

### Behavior

1. Look up user by email. Fail with error if not found.
2. Generate a random 12-character alphanumeric password (or use
   `--password` if provided).
3. Hash it with bcrypt via `hash_password()`.
4. Update the user's `password_hash` and set `password_expires_at` to
   `now + expires_hours` (default: 24 hours).
5. Print the temporary password to stdout in a clear format:

```
Password reset for user@example.com
Temporary password: Xk9mP2nQ4rTs
Expires at: 2026-09-08 12:00:00
User must change password on next login.
```

### Implementation Details

- Use `secrets.token_urlsafe(9)` for random password generation (yields
  12 chars, URL-safe but readable enough to communicate verbally).
- Reuse existing `hash_password()` from `src/auth/passwords.py`.
- Reuse existing `repo.update_user()` which already supports
  `password_hash` and `password_expires_at` kwargs.
- The login endpoint already handles `password_expires_at` -- it returns
  `password_expired: true` and a 5-minute token. No API changes needed.

### Also add a repository helper

Add `repo.reset_user_password(email, password_hash, expires_at)` to
`src/database/repository.py` as a convenience wrapper around
`update_user()` that:
1. Looks up user by email.
2. Raises `ValueError` if not found.
3. Updates `password_hash` and `password_expires_at`.
4. Returns the updated user.

This keeps the CLI command thin.

## Dev Notes

- Follow the pattern of the existing `seed-users` command (uses `@cli.command`,
  `@click.option("--db")`, creates a Repository).
- The `password_expires_at` field already exists on `UserRow` (added for
  admin-created temp passwords). This reuses that mechanism.
- Do NOT add any API endpoint here. That is T07.

## Testing

Create `tests/cli/test_reset_password.py`:

1. Test happy path: user exists, password is reset, `password_expires_at`
   is set, output contains temp password.
2. Test user not found: prints error, exits with code 1.
3. Test custom password via `--password` flag.
4. Test custom expiry via `--expires-hours` flag.
5. Test that the generated password verifies against the stored hash.

Use `click.testing.CliRunner` for CLI tests.

Expected: ~6-8 tests.

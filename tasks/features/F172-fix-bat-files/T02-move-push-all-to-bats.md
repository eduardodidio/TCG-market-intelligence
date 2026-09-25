# T02 — Move push-all.bat into bats/ directory

**Wave:** 0
**Status:** planned

## User Story

As a developer, I want all operational bat files to live in the `bats/` directory so the project layout is consistent and `setup-schedule.bat` can reference a single directory.

## Context

`push-all.bat` currently sits at the repo root. It runs `liga-sweep --max-age-days 1`. All other operational bats already live in `bats/`. Moving it there keeps everything consistent.

## Dev Notes

1. `git mv push-all.bat bats/push-all.bat`.
2. Update the `cd` line from `cd /d "%~dp0"` to `cd /d "%~dp0\.."` (since it will now be one directory deeper).
3. Verify no other file references the old root path. If `setup-schedule.bat` does, T03 handles it.
4. Keep the `pause` at the end since this is a manual-run script (user double-clicks it).

## Testing

- `bats/push-all.bat` exists, old `push-all.bat` does not.
- Running `cd /d <repo_root> && python -m src.cli.main liga-sweep --help` succeeds (validates the CLI command).

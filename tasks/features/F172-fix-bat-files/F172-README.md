# F172 — Audit and fix all .bat files

**Status:** planned
**Branch:** homol
**Scope:** Housekeeping — fix broken paths, remove security risk, update scheduler

## Problem

Several `.bat` files have issues:
1. `push-prices.bat` is deprecated but contains a **hardcoded API key** (security risk).
2. `setup-schedule.bat` references wrong paths (`root\daily-scan.bat` instead of `bats\daily-scan.bat`) and only schedules 3 tasks when there are now 7 bat files in `bats/`.
3. `push-all.bat` sits at root level while all active bats live in `bats/` — inconsistent.

The `bats/` directory files (daily-scan, process-queue, banlist-sync, collect-metagame, daily-snapshot, deck-suggestions, fetch-news) are all correct — they use `cd /d "%~dp0\.."` and call valid CLI commands.

## Inventory

| File | Location | Status |
|------|----------|--------|
| `push-all.bat` | root | OK but inconsistent location |
| `push-prices.bat` | root | DEPRECATED + hardcoded API key |
| `setup-schedule.bat` | root | Wrong paths + missing schedules |
| `bats/daily-scan.bat` | bats/ | OK |
| `bats/process-queue.bat` | bats/ | OK |
| `bats/banlist-sync.bat` | bats/ | OK |
| `bats/collect-metagame.bat` | bats/ | OK |
| `bats/daily-snapshot.bat` | bats/ | OK |
| `bats/deck-suggestions.bat` | bats/ | OK |
| `bats/fetch-news.bat` | bats/ | OK |

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| T01 | Delete deprecated `push-prices.bat` (hardcoded API key) | 0 |
| T02 | Move `push-all.bat` into `bats/` for consistency | 0 |
| T03 | Rewrite `setup-schedule.bat` with correct paths + all 7 bats | 0 |

All tasks are independent — single wave.

## Wave 0 (all parallel)

- **T01** — Remove `push-prices.bat`. It is deprecated (header says so), contains a hardcoded secret, and references a CLI command (`push-prices`) that may no longer exist.
- **T02** — Move `push-all.bat` to `bats/push-all.bat`, update `cd` to use `"%~dp0\.."` like all other bats in that directory.
- **T03** — Rewrite `setup-schedule.bat` to: (a) point all paths to `bats\` directory, (b) schedule all 7 bats with sensible times, (c) delete stale task names before recreating.

## Acceptance Criteria

- No `.bat` file at root level contains hardcoded secrets.
- `setup-schedule.bat` references correct `bats\` paths for all scheduled tasks.
- Every bat in `bats/` can be validated by running its CLI command with `--help` (no import errors).
- `push-prices.bat` no longer exists in the repo.

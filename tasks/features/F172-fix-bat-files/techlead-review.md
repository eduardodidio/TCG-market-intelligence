# F172 Tech Lead Review — Audit and fix all .bat files

**Reviewer:** Tech Lead
**Date:** 2026-09-25
**Verdict:** APPROVED

---

## T01 — Delete deprecated push-prices.bat

**Status:** PASS

- `push-prices.bat` no longer exists at root (confirmed via filesystem check).
- `git log --all -- push-prices.bat` shows the file existed historically but is removed on the current branch.
- `grep` across all `.bat` files for `api[_-]?key|token|secret|password|Bearer` returns zero matches -- no hardcoded secrets remain in any bat file.

## T02 — Move push-all.bat into bats/

**Status:** PASS

- Root `push-all.bat` is gone.
- `bats/push-all.bat` exists with correct content.
- The `cd` line uses `cd /d "%~dp0\.."` (line 9), consistent with all other bats in the directory.
- The `liga-sweep --max-age-days 1` command is confirmed present in CLI (`python -m src.cli.main --help`).
- Retains `pause` at the end (correct for manual-run scripts).
- `.gitignore` already covers the entire `bats/` directory (line 43), so the moved file is correctly gitignored.

## T03 — Rewrite setup-schedule.bat

**Status:** PASS

- All 8 scheduled tasks are present with correct paths using `%~dp0bats\<name>.bat` pattern. No hardcoded absolute paths found.
- Schedule summary (verified against the file):
  - `TEDHC_DeckSuggestions` -- 03:00 daily
  - `TEDHC_BanlistSync` -- 06:00 weekly Monday
  - `TEDHC_CollectMetagame` -- 06:30 weekly Monday
  - `TEDHC_FetchNews` -- 08:00 daily
  - `TEDHC_DailyScan` -- 09:00 daily
  - `TEDHC_ProcessQueue_14h` -- 14:00 daily
  - `TEDHC_ProcessQueue_17h` -- 17:00 daily
  - `TEDHC_DailySnapshot` -- 23:30 daily
- Clean-slate deletion block (lines 12-21) removes all 10 possible task names (8 active + `TEDHC_PushAll` + `TEDHC_ProcessQueue_18h` legacy stubs), preventing orphaned scheduler entries.
- `push-all.bat` correctly excluded from scheduling (manual-only), documented in the summary block at the end.
- Every `/tr` path uses the `%~dp0bats\` prefix -- paths are relative to script location.

## CLI Command Cross-Check

All commands referenced in `bats/*.bat` verified against `python -m src.cli.main --help`:

| Bat file | CLI command | Exists |
|----------|-------------|--------|
| daily-scan.bat | `liga-sweep`, `process-price-requests`, `snapshot-portfolio` | Yes, Yes, Yes |
| process-queue.bat | `process-price-requests` | Yes |
| banlist-sync.bat | `banlist-sync` | Yes |
| collect-metagame.bat | `collect-metagame` | Yes |
| daily-snapshot.bat | `daily-snapshot` | Yes |
| deck-suggestions.bat | `process-deck-suggestions` | Yes |
| fetch-news.bat | `fetch-news` | Yes |
| push-all.bat | `liga-sweep` | Yes |

## Existing bats/ files

Confirmed the 7 pre-existing bat files in `bats/` were NOT modified by this feature (they all predate the F172 commits). All use the consistent `cd /d "%~dp0\.."` pattern.

## Minor Observations (non-blocking)

1. **F172 naming collision**: There are two directories under `tasks/features/` named `F172-*` (`F172-fix-bat-files` and `F172-deck-builder-suggestions`). This is a feature numbering clash but does not affect functionality.
2. **deck-suggestions.bat comment says "F172"**: Line 2 references `(F172)` which refers to the deck-builder-suggestions feature, not the bat-file fix feature. This is accurate for when that file was created -- not a bug.
3. **`.gitignore` covers `setup-schedule.bat`** (line 46): The scheduler script is gitignored, meaning changes to it are not tracked. This is intentional (it contains local Task Scheduler configuration), but worth noting that future edits to this file require explicit `git add -f` to commit.

## Security

- Zero hardcoded secrets in any `.bat` file (grep confirmed).
- All environment-dependent values (DATABASE_URL, ANTHROPIC_API_KEY) are loaded from `.env` via `src/config.py`.
- `.env` is in `.gitignore`.

---

**Verdict: APPROVED** -- All three tasks executed correctly. Security risk eliminated, paths standardized, scheduler complete.

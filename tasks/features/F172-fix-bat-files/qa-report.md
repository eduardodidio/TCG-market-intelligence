# F172 QA Report -- Audit and fix all .bat files

**QA Agent** | 2026-09-25
**Verdict: PASS**

---

## Checks Performed

### 1. T01 -- push-prices.bat deleted

| Check | Result |
|-------|--------|
| `push-prices.bat` does not exist at project root | PASS |
| No references to `push-prices.bat` in any remaining bat file | PASS |

### 2. T02 -- push-all.bat moved to bats/

| Check | Result |
|-------|--------|
| `push-all.bat` does NOT exist at project root | PASS |
| `bats/push-all.bat` EXISTS | PASS |
| Uses `cd /d "%~dp0\.."` (line 9) | PASS |
| Calls `liga-sweep --max-age-days 1` (valid CLI command) | PASS |
| Ends with `pause` (correct for manual-run script) | PASS |

### 3. T03 -- setup-schedule.bat rewritten

| Check | Result |
|-------|--------|
| All 8 `/tr` paths use `%~dp0bats\<name>.bat` pattern | PASS (lines 27, 35, 43, 51, 59, 67, 75, 83) |
| Zero hardcoded `C:\...` absolute paths | PASS |
| Clean-slate deletion block removes 10 task names (8 active + 2 legacy) | PASS (lines 12-21) |
| `push-all.bat` excluded from scheduling (manual only, documented) | PASS (line 107) |
| Summary block matches actual scheduled tasks | PASS |

### 4. Security -- no hardcoded secrets

| Check | Result |
|-------|--------|
| Grep for `api[_-]?key\|token\|secret\|password\|bearer` across all `.bat` files | PASS -- zero matches |
| `deck-suggestions.bat` mentions `ANTHROPIC_API_KEY` only in a comment saying "put it in .env, never in this file" | PASS -- informational only, no value exposed |

### 5. Consistent `cd /d` pattern across all bats/

All 8 files in `bats/` use `cd /d "%~dp0\.."`:

- `daily-scan.bat` (line 7)
- `process-queue.bat` (line 7)
- `banlist-sync.bat` (line 7)
- `collect-metagame.bat` (line 14)
- `daily-snapshot.bat` (line 7)
- `deck-suggestions.bat` (line 18)
- `fetch-news.bat` (line 8)
- `push-all.bat` (line 9)

### 6. CLI command validation

Every CLI command referenced in `bats/*.bat` was verified with `--help` (no import errors):

| Bat file | Command(s) | --help OK |
|----------|-----------|-----------|
| push-all.bat | `liga-sweep` | Yes |
| daily-scan.bat | `liga-sweep`, `process-price-requests`, `snapshot-portfolio` | Yes, Yes, Yes |
| process-queue.bat | `process-price-requests` | Yes |
| banlist-sync.bat | `banlist-sync` | Yes |
| collect-metagame.bat | `collect-metagame` | Yes |
| daily-snapshot.bat | `daily-snapshot` | Yes |
| deck-suggestions.bat | `process-deck-suggestions` | Yes |
| fetch-news.bat | `fetch-news` | Yes |

---

## Summary

All three tasks (T01, T02, T03) executed correctly:

- **T01**: `push-prices.bat` deleted -- security risk eliminated.
- **T02**: `push-all.bat` moved to `bats/` with correct `cd` path.
- **T03**: `setup-schedule.bat` rewritten with all 8 tasks, relative paths, clean-slate deletion, and accurate summary block.

No hardcoded secrets, no broken CLI references, consistent directory conventions across all bat files.

**Verdict: PASS**

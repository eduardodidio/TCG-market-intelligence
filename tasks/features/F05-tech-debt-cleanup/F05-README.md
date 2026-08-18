# F05 — Technical Debt Cleanup

**Status:** done
**Created:** 2026-08-18

## Goal

Resolve accumulated technical debt before starting F05 (REST API). Priority
is hardening test coverage (especially `provider.py` at 63% and `parsers/myp.py`
at 82%), followed by missing documentation artifacts (PRDs, diagrams) and
housekeeping (.gitignore, stale status fields).

## Debt Inventory

| Item | Current | Target | Priority |
|------|---------|--------|----------|
| `providers/myp/provider.py` coverage | 63% | >= 85% | HIGH |
| `parsers/myp.py` coverage | 82% | >= 90% | HIGH |
| `cli/main.py` coverage | 77% | >= 85% | MEDIUM |
| `collectors/backfill.py` coverage | 89% | >= 90% | LOW |
| Overall coverage | 86% | >= 90% | HIGH |
| PRD for F02 | missing | `docs/prd/F02-*.md` | MEDIUM |
| PRD for F03 | missing | `docs/prd/F03-*.md` | MEDIUM |
| PRD for F04 | missing | `docs/prd/F04-*.md` | MEDIUM |
| F04 diagrams | missing | `docs/diagrams/F04-*.mmd` | MEDIUM |
| `.coverage` in .gitignore | missing | added | LOW |
| F03-README status | says "planned" | should say "done" | LOW |

## Architecture Impact

No new modules. This feature only adds test files, documentation files, and
minor edits to existing config/metadata.

## Global Acceptance Criteria

1. **AC1** Overall test coverage >= 90%
2. **AC2** `provider.py` coverage >= 85% (mock-based tests for `_fetch`, `discover_sets`, `discover_cards`, `get_card_details`, `get_current_price`, `get_price_history`)
3. **AC3** `parsers/myp.py` coverage >= 90%
4. **AC4** `cli/main.py` coverage >= 85%
5. **AC5** All existing 131 tests still pass
6. **AC6** PRDs exist for F02, F03, F04 in `docs/prd/`
7. **AC7** `F04-architecture.mmd` and `F04-journey.mmd` exist in `docs/diagrams/`
8. **AC8** `.coverage` is in `.gitignore`
9. **AC9** F03-README.md status updated to "done"

## Waves

- **Wave 0**: F05-T01 (housekeeping — .gitignore, status fix)
- **Wave 1**: F05-T02, F05-T03, F05-T04 (test coverage — provider, parsers, CLI — parallel)
- **Wave 2**: F05-T05, F05-T06 (docs — PRDs, F04 diagrams — parallel)

## Tasks

| Wave | Task    | Type  | Description                                      | Status  |
|------|---------|-------|--------------------------------------------------|---------|
| 0    | F05-T01 | chore | Housekeeping: .gitignore + F03 status fix        | planned |
| 1    | F05-T02 | test  | Provider test coverage (mock _fetch, all methods)| planned |
| 1    | F05-T03 | test  | Parser test coverage (uncovered branches)        | planned |
| 1    | F05-T04 | test  | CLI test coverage (untested subcommands)         | planned |
| 2    | F05-T05 | docs  | Missing PRDs for F02, F03, F04                   | planned |
| 2    | F05-T06 | docs  | F04 diagrams (architecture + journey)            | planned |

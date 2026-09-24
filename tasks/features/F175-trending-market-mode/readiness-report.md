# Readiness Report — F175 trending-market-mode

**Generated:** 2026-09-24T00:00:00Z
**Feature dir:** tasks/features/F175-trending-market-mode/
**Total tasks audited:** 8
**Total ACs declared:** 7

## Check 1 — AC coverage (every AC has ≥1 task)
| AC ID | Status | Tasks covering | Detail |
|-------|--------|-----------------|--------|
| AC1   | PASS   | T03, T07        |        |
| AC2   | PASS   | T03, T07        |        |
| AC3   | PASS   | T03, T07        |        |
| AC4   | PASS   | T04, T07        |        |
| AC5   | PASS   | T02             |        |
| AC6   | PASS   | T05             |        |
| AC7   | PASS   | T01, T06, T08   |        |

## Check 2 — Bidirectional traceability (every task cites ≥1 AC)
| Task | Status | ACs cited | Detail |
|------|--------|-----------|--------|
| F175-T01 | PASS | AC7 | `**Maps to AC:** AC7` |
| F175-T02 | PASS | AC5 | `**Maps to AC:** AC5` |
| F175-T03 | PASS | AC1, AC2, AC3 | `**Maps to AC:** AC1, AC2, AC3` |
| F175-T04 | PASS | AC4 | `**Maps to AC:** AC4` |
| F175-T05 | PASS | AC6 | `**Maps to AC:** AC6` |
| F175-T06 | PASS | AC7 | `**Maps to AC:** AC7` |
| F175-T07 | PASS | AC1, AC2, AC3, AC4 | `**Maps to AC:** AC1, AC2, AC3, AC4` |
| F175-T08 | PASS | AC7 | `**Maps to AC:** AC7` |

## Check 3 — File collision (same-Wave tasks don't share files)
| Wave | Status | Colliding paths | Tasks involved |
|------|--------|-----------------|-----------------|
| 0    | PASS   | (none)          |                 |
| 1    | PASS   | (none)          |                 |
| 2    | PASS   | (none)          |                 |

Wave 0: T01 (`docs/prd/F175-trending-market-mode.md`) vs T02 (`scripts/diagnose_trending_f175.py`,
`tests/unit/scripts/test_diagnose_trending_f175.py`) — no overlap.

Wave 1: T03 (`src/database/trending_queries.py`, `src/database/repository.py`,
`tests/unit/database/test_trending_queries.py`), T04 (`src/services/trending.py`,
`tests/unit/services/test_trending_service_cache_f175.py`), T05
(`frontend/src/pages/__tests__/TrendingCollectionToggle.test.tsx`, conditionally
`frontend/src/components/TrendingSection.tsx` / `frontend/src/hooks/useApi.ts`), T06
(`docs/diagrams/F175-architecture.mmd`, `docs/diagrams/F175-journey.mmd`) — no shared path.

Wave 2: T07 (`tests/unit/api/test_f175_trending_market_mode.py`) vs T08 (`README.md`) — no overlap.

## Check 4 — Wave 0 completeness (deps/perms/scaffolding)
| Item needed by Wave≥1 | Status | Wave 0 covers? | Detail |
|------------------------|--------|-----------------|--------|
| (none found) | PASS | n/a | All directories referenced by Wave 1/2 tasks already exist in the repo: `tests/unit/database/`, `tests/unit/services/`, `tests/unit/api/`, `frontend/src/pages/__tests__/`, `docs/diagrams/`, `docs/prd/template.md` (confirmed via `ls`). No `mkdir`, `npm install`/`pip install`, or permission/settings changes are requested by any Wave≥1 task. The one genuinely new directory (`tests/unit/scripts/`, needed by T02) is created within T02 itself, which is a Wave 0 task, so it is not a Wave≥1 dependency on Wave 0. |

## Check 5 — Testing section non-empty
| Task | Status | Detail |
|------|--------|--------|
| F175-T01 | PASS | 3 non-empty lines under `## Testing`, cites `test -f`, `git branch --show-current`, `ruff check src/`, `pytest tests/ -q`. |
| F175-T02 | PASS | Cites `pytest` and the exact new test path/command. |
| F175-T03 | PASS | Cites `pytest` fixture conventions and two run commands. |
| F175-T04 | PASS | Cites `pytest`, `unittest.mock.MagicMock`, time-patching technique, and a run command. |
| F175-T05 | PASS | Cites Vitest + @testing-library/react + user-event, a targeted `npx vitest run` command, and the full-suite `npm test`/`npm run build` commands. |
| F175-T06 | PASS | 3 non-empty lines: no-pytest note, `npx -y @mermaid-js/mermaid-cli` syntax check, and an `ls` existence check. |
| F175-T07 | PASS | Cites pytest + FastAPI TestClient framework, a targeted run command, and full-suite `pytest`/`ruff` commands. |
| F175-T08 | PASS | 3 non-empty lines: docs-only note, `git diff README.md` check, and `pytest tests/ -q` / `npm test` re-confirmation. |

## Summary
- PASS: 25
- FAIL: 0

**Verdict:** READY

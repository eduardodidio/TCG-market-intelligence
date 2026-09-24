# Readiness Report — F178 news-collection-bat

**Generated:** 2026-09-24T00:00:00Z
**Feature dir:** tasks/features/F178-news-collection-bat/
**Total tasks audited:** 8
**Total ACs declared:** 10

## Check 1 — AC coverage (every AC has ≥1 task)
| AC ID | Status | Tasks covering | Detail |
|-------|--------|-----------------|--------|
| AC1   | PASS   | T02, T04        |        |
| AC2   | PASS   | T04             |        |
| AC3   | PASS   | T04             |        |
| AC4   | PASS   | T07             |        |
| AC5   | PASS   | T03             |        |
| AC6   | PASS   | T03             |        |
| AC7   | PASS   | T05             |        |
| AC8   | PASS   | T07, T08        |        |
| AC9   | PASS   | T01, T06, T07   |        |
| AC10  | PASS   | T08             |        |

## Check 2 — Bidirectional traceability (every task cites ≥1 AC)
| Task | Status | ACs cited      | Detail |
|------|--------|----------------|--------|
| T01  | PASS   | AC9            |        |
| T02  | PASS   | AC1            |        |
| T03  | PASS   | AC5, AC6       |        |
| T04  | PASS   | AC1, AC2, AC3  |        |
| T05  | PASS   | AC7            |        |
| T06  | PASS   | AC9            |        |
| T07  | PASS   | AC4, AC8, AC9  |        |
| T08  | PASS   | AC8, AC10      |        |

## Check 3 — File collision (same-Wave tasks don't share files)
| Wave | Status | Colliding paths | Tasks involved |
|------|--------|------------------|-----------------|
| 0    | PASS   | (none)           | T01 only |
| 1    | PASS   | (none)           | T02 (`news_fetcher.py`, its test), T03 (`repository.py` news section, `routers/news.py`, its test), T05 (frontend `news.ts`, `NewsPage.tsx`, its test, `en.json`/`pt-BR.json` news block), T06 (both `.mmd` files) — no shared paths |
| 2    | PASS   | (none)           | T04 only |
| 3    | PASS   | (none)           | T07 only |
| 4    | PASS   | (none)           | T08 only |

Note: T02 and T08 both touch `src/services/news_fetcher.py`, but they are in different Waves (1 and 4) with T08 depending transitively on T02 via T07 — not a same-Wave collision.

## Check 4 — Wave 0 completeness (deps/perms/scaffolding)
| Item needed by Wave≥1 | Status | Wave 0 covers? | Detail |
|------------------------|--------|-----------------|--------|
| `tests/fixtures/news/` directory (consumed by T02; referenced by T04's brief) | PASS | Yes | T01 (Wave 0) explicitly creates it: "Fixtures dir `tests/fixtures/news/` does not exist yet — create it." |
| New pip/npm dependency | PASS | N/A — none required | README states "Dependencies: none added"; T01 explicitly notes `httpx`/`click` already declared, do not add `feedparser` |
| `.claude/settings.json` / permission change | PASS | N/A — none required | T01 explicitly notes no settings change needed; only pytest/npm/ruff/CLI commands used across all waves |
| `bats/` directory (T07 adds `bats/fetch-news.bat`) | PASS | Pre-existing in repo | Verified: `bats/process-queue.bat` already exists |
| `docs/adr/` directory (T07 adds new ADR) | PASS | Pre-existing in repo | Verified: `docs/adr/0013-*.md` etc. already exist |
| `# ── News feed (F166)` section in `repository.py` (T03 appends here) | PASS | Pre-existing in repo | Verified at `src/database/repository.py:5037` |

## Check 5 — Testing section non-empty
| Task | Status | Detail |
|------|--------|--------|
| T01  | PASS   | 3 lines; commands: `python -c ...`, `test -f ...`, `pytest tests/ -q --co` |
| T02  | PASS   | 3 lines; framework pytest, explicit coverage command |
| T03  | PASS   | 3 lines; pytest commands given |
| T04  | PASS   | 3 lines; pytest + click.testing.CliRunner, explicit run command |
| T05  | PASS   | 3 lines; Vitest + Testing Library, explicit run commands |
| T06  | PASS   | 3 lines; docs-only plan with a concrete verification command (`ls docs/diagrams/...`) — not a placeholder |
| T07  | PASS   | 3 lines; new pytest test plus explicit run commands |
| T08  | PASS   | 3 lines; live + automated + regression commands specified |

## Summary
- PASS: 34
- FAIL: 0

**Verdict:** READY

# Readiness Report — F176 collection-price-history

**Generated:** 2026-09-24T13:45:29Z
**Feature dir:** tasks/features/F176-collection-price-history/
**Total tasks audited:** 12
**Total ACs declared:** 14

## Check 1 — AC coverage (every AC has ≥1 task)
| AC ID | Status | Tasks covering | Detail |
|-------|--------|-----------------|--------|
| AC1   | PASS   | T01             |        |
| AC2   | PASS   | T02             |        |
| AC3   | PASS   | T03, T07, T08, T12 |     |
| AC4   | PASS   | T03, T07, T12   |        |
| AC5   | PASS   | T03, T07        |        |
| AC6   | PASS   | T06             |        |
| AC7   | PASS   | T05, T11        |        |
| AC8   | PASS   | T05             |        |
| AC9   | PASS   | T04, T08, T09   |        |
| AC10  | PASS   | T04, T10        |        |
| AC11  | PASS   | T12             |        |
| AC12  | PASS   | T11, T12        |        |
| AC13  | PASS   | T02, T11        |        |
| AC14  | PASS   | T05, T07        |        |

## Check 2 — Bidirectional traceability (every task cites ≥1 AC)
| Task | Status | ACs cited | Detail |
|------|--------|-----------|--------|
| T01  | PASS   | AC1       |        |
| T02  | PASS   | AC2, AC13 |        |
| T03  | PASS   | AC3, AC4, AC5 |    |
| T04  | PASS   | AC9, AC10 |        |
| T05  | PASS   | AC7, AC8, AC14 |   |
| T06  | PASS   | AC6       |        |
| T07  | PASS   | AC3, AC4, AC5, AC14 | |
| T08  | PASS   | AC3, AC9  |        |
| T09  | PASS   | AC9       |        |
| T10  | PASS   | AC10      |        |
| T11  | PASS   | AC7, AC12, AC13 |  |
| T12  | PASS   | AC3, AC4, AC11, AC12 | |

## Check 3 — File collision (same-Wave tasks don't share files)
| Wave | Status | Colliding paths | Tasks involved |
|------|--------|------------------|-----------------|
| 0    | PASS   | (none)           | T01 only        |
| 1    | PASS   | (none)           | T02, T03, T04, T05 — disjoint paths (docs/adr, docs/diagrams vs. src/collection vs. src/api/schemas vs. src/collectors/price_snapshot.py) |
| 2    | PASS   | (none)           | T06 (src/collectors/liga_sweep.py), T07 (src/services/collection_price_history.py), T10 (frontend/*) — disjoint. T06's Dev Notes mention `main.py`/`app.py` only to say they are explicitly NOT edited |
| 3    | PASS   | (none)           | T08 (src/api/routers/collection.py), T09 (src/api/routers/cards.py) — disjoint files |
| 4    | PASS   | (none)           | T11 (src/cli/main.py, bats/daily-snapshot.bat, README.md), T12 (tests/integration/test_collection_price_history.py) — disjoint |

## Check 4 — Wave 0 completeness (deps/perms/scaffolding)
| Item needed by Wave≥1 | Status | Wave 0 covers? | Detail |
|------------------------|--------|----------------|--------|
| `tests/scripts/`, `tests/collection/`, `tests/services/`, `tests/collectors/`, `tests/integration/`, `frontend/src/components/__tests__/` (test dirs used by T03/T05–T07/T09/T10/T12) | PASS | Yes — T01 explicitly confirms existence of all six directories as its setup checklist | |
| New pip/npm dependencies | PASS | N/A | README Setup notes state "Sem dependências novas (pip/npm)"; no task introduces a new dependency |
| `bats/` directory for T11's new `.bat` file | PASS | Pre-existing | `bats/process-queue.bat` already exists and is used as the template; T11 only notes it must `git add -f` since `bats/` is gitignored — no new directory creation needed |
| Permissions / settings.json changes | PASS | N/A | No task requires new permissions |

## Check 5 — Testing section non-empty
| Task | Status | Detail |
|------|--------|--------|
| T01  | PASS   | pytest command + fixture pattern, ≥3 lines |
| T02  | PASS   | Docs-only but names ruff command + Mermaid validation, ≥3 lines |
| T03  | PASS   | pytest + coverage command |
| T04  | PASS   | pytest command |
| T05  | PASS   | pytest command + fixture + frozen date |
| T06  | PASS   | pytest + asyncio pattern |
| T07  | PASS   | pytest + coverage command |
| T08  | PASS   | pytest + TestClient pattern |
| T09  | PASS   | pytest + TestClient pattern |
| T10  | PASS   | Vitest command |
| T11  | PASS   | pytest + CliRunner pattern |
| T12  | PASS   | pytest + FastAPI TestClient pattern |

## Summary
- PASS: 12 (Check1: 14/14 ACs, Check2: 12/12 tasks, Check3: 5/5 waves, Check4: 4/4 items, Check5: 12/12 tasks)
- FAIL: 0

**Verdict:** READY

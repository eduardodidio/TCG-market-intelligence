# F04 Readiness Report

**Feature:** F04 -- Collector Scaling: Batch Upsert, Concurrency, Integration Tests
**Date:** 2026-08-18
**Auditor:** Readiness Agent

---

## Check 1 -- AC Coverage

Every AC declared in the README (AC1-AC7) must be referenced by at least one task.

| AC  | Referenced by | Result |
|-----|---------------|--------|
| AC1 | F04-T01       | PASS   |
| AC2 | F04-T02       | PASS   |
| AC3 | F04-T02       | PASS   |
| AC4 | F04-T03       | PASS   |
| AC5 | F04-T01, F04-T02, F04-T03 | PASS |
| AC6 | F04-T01       | PASS   |
| AC7 | F04-T02       | PASS   |

**Result: PASS** -- All 7 acceptance criteria are covered by at least one task.

---

## Check 2 -- Bidirectional Traceability

Every task must have a non-empty "Maps to AC" field.

| Task    | Maps to AC        | Result |
|---------|-------------------|--------|
| F04-T01 | AC1, AC5, AC6     | PASS   |
| F04-T02 | AC2, AC3, AC5, AC7| PASS   |
| F04-T03 | AC4, AC5          | PASS   |

**Result: PASS** -- All tasks have non-empty AC mappings.

---

## Check 3 -- File Collision (same Wave)

No two tasks in the same Wave should touch the same file.

| Wave | Tasks   | Files touched | Collision? |
|------|---------|---------------|------------|
| 0    | F04-T01 | `src/database/repository.py`, `tests/unit/test_repository.py` | N/A (single task) |
| 1    | F04-T02 | `src/collectors/backfill.py`, `src/cli/main.py`, `tests/unit/test_backfill.py`, `docs/diagrams/F01-architecture.mmd`, `docs/diagrams/F01-journey.mmd` | N/A (single task) |
| 2    | F04-T03 | `tests/integration/__init__.py`, `tests/integration/test_collector_pipeline.py` | N/A (single task) |

**Result: PASS** -- Each Wave contains exactly one task, so no file collisions are possible.

---

## Check 4 -- Wave 0 Completeness

Every directory, dependency, or permission needed by Wave >= 1 tasks must be created in a Wave 0 task or already exist in the repo.

| Prerequisite | Needed by | Provided by | Exists in repo? | Result |
|--------------|-----------|-------------|-----------------|--------|
| `src/database/repository.py` | T01 (Wave 0) | -- (existing) | Yes | PASS |
| `src/collectors/backfill.py` | T02 (Wave 1) | -- (existing) | Yes | PASS |
| `src/cli/main.py` | T02 (Wave 1) | -- (existing) | Yes | PASS |
| `tests/integration/` directory | T03 (Wave 2) | -- | Yes (exists but empty) | PASS |
| `tests/integration/__init__.py` | T03 (Wave 2) | T03 creates it | No (not present) | WARN |
| pytest-asyncio dependency | T02, T03 | -- (existing dep) | Yes (in pyproject.toml) | PASS |
| Batch upsert (T01 output) | T02 (Wave 1) | T01 (Wave 0) | -- | PASS |
| T01 + T02 outputs | T03 (Wave 2) | T01 (Wave 0), T02 (Wave 1) | -- | PASS |

**Result: PASS** -- The `tests/integration/` directory already exists in the repo. The `__init__.py` is absent but T03 itself declares it will create it, and since T03 is the only task in Wave 2, this is self-contained. No external prerequisite is missing.

Note: The `tests/integration/` directory exists but is empty (no `__init__.py`). T03 explicitly states "create `__init__.py`" in its Dev Notes. This is acceptable since T03 is the task that uses it.

---

## Check 5 -- Testing Section Non-Empty

Every task must have a Testing section with >= 3 non-empty lines mentioning a command or framework.

| Task    | Testing lines | Framework mentioned | Command mentioned | Result |
|---------|---------------|--------------------|--------------------|--------|
| F04-T01 | 3 lines       | pytest             | `python -m pytest tests/unit/test_repository.py -v` | PASS |
| F04-T02 | 4 lines       | pytest, pytest-asyncio | `python -m pytest tests/unit/test_backfill.py -v` | PASS |
| F04-T03 | 3 lines       | pytest, pytest-asyncio | `python -m pytest tests/integration/ -v` | PASS |

**Result: PASS** -- All tasks have adequate Testing sections.

---

## Summary

| Check | Description                | Result |
|-------|----------------------------|--------|
| 1     | AC coverage                | PASS   |
| 2     | Bidirectional traceability | PASS   |
| 3     | File collision             | PASS   |
| 4     | Wave 0 completeness        | PASS   |
| 5     | Testing section non-empty  | PASS   |

**Verdict:** READY

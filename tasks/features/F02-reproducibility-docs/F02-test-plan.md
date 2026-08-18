# F02 Test Plan

**Status:** retroactive
**Generator:** TEA
**Generated at:** 2026-08-18
**Source brief:** `tasks/features/F02-reproducibility-docs/F02-README.md`
**Feature:** F02 -- Project Reproducibility & Living Documentation
**Test count at ship time:** 27 (all passing per QA report)

---

## 1. Fixtures

F02 is a docs/tooling feature (Makefile, bootstrap scripts, 11 documentation files, ADR-0002). No runtime code was written, therefore no test fixtures were created or required.

| Fixture | Path | Domain | Owner |
|---------|------|--------|-------|
| _(none)_ | -- | -- | -- |

_Justification: F02 produces only static files (Makefile, shell scripts, Markdown docs, Mermaid diagrams). No domain objects, database state, or HTTP responses are exercised, so no fixtures are warranted._

---

## 2. Harnesses por fronteira

### Unit

- **Framework:** pytest
- **Command:** `make test` (delegates to `.venv/bin/python -m pytest tests/ -v`)
- **Default test path:** `tests/`
- **Note:** The 27 tests at F02 ship time belong to F01 (MYP collector). F02 itself introduced zero new unit tests because it produced no testable Python code. The existing suite serves as a regression gate -- `make test` passing is acceptance criterion AC2.

### Integration

**N/A** -- F02 does not integrate components. The closest analog is the manual validation of `make setup && make test && make lint` on a fresh environment, which is a smoke test rather than an automated integration harness.

### E2E

**N/A** -- F02 has no user-facing runtime behavior. The "end-to-end" validation is running the bootstrap script on a clean machine and verifying the full `make setup -> make test -> make run-backfill` chain works. This was validated manually by QA and is not automatable without a CI pipeline (which did not exist at F02 time).

---

## 3. Perf budgets

_Sem perf budgets aplicaveis._

F02 produces documentation and build tooling. No latency, throughput, or resource consumption thresholds apply.

---

## 4. Mocks vs hits real

| Componente | Decisao | Justificativa |
|------------|---------|---------------|
| _(none)_ | -- | -- |

_F02 has no external dependencies to mock or hit. No HTTP calls, no database writes, no filesystem operations beyond creating static files. The existing F01 test suite (27 tests) already handles its own mock/real decisions independently of F02._

---

## 5. Test scenarios resumo

All F02 test scenarios are **manual validations** (file existence, cross-link integrity, content accuracy). They were executed by QA at ship time. Listed below for traceability:

### T01 -- Makefile + .env.example + pyproject.toml (F02-T01)

1. `make setup` creates venv and installs all deps on fresh clone
2. `make test` runs 27+ tests, all green
3. `make lint` passes with zero violations
4. `make clean` removes all generated artifacts
5. `make help` shows formatted target list
6. `.env.example` can be copied to `.env` without modification and collector works with defaults

### T02 -- Bootstrap scripts (F02-T02)

7. Mac with Homebrew + Python present: script skips installs
8. Linux (Debian) with Python present: script skips apt install
9. Missing Python: script installs or prints clear guidance
10. `.env` already exists: script does not overwrite it
11. Re-run after successful first run: no errors, no side effects

### T03 -- ARCHITECTURE.md (F02-T03)

12. Every `src/` path mentioned in the doc exists in the repo
13. Every ADR referenced exists under `docs/adr/`
14. Mermaid code block renders correctly (valid syntax)
15. A new contributor can understand where to add a new provider

### T04 -- SETUP.md + DEVELOPMENT.md (F02-T04)

16. SETUP.md references only existing files (bootstrap scripts, Makefile, .env.example)
17. DEVELOPMENT.md ruff config matches pyproject.toml
18. All `make` targets mentioned exist in Makefile
19. Commands use correct module paths (`src.cli.main`, not `src/cli/main.py`)

### T05 -- DATA_SOURCES.md + DATABASE.md (F02-T05)

20. Every table in DATABASE.md exists in `src/database/models.py`
21. Every column documented has the correct type
22. MYP Cards URL patterns match provider.py implementation
23. ER diagram is valid Mermaid syntax
24. Cross-links between docs are not broken

### T06 -- SECURITY.md + CONTRIBUTING.md + AI_CONTEXT.md (F02-T06)

25. SECURITY.md guardrails do not contradict CLAUDE.md
26. CONTRIBUTING.md links point to existing docs
27. AI_CONTEXT.md tech stack matches pyproject.toml dependencies
28. AI_CONTEXT.md architecture summary matches ARCHITECTURE.md

### T07 -- API.md + ROADMAP.md + DECISIONS.md (F02-T07)

29. DECISIONS.md ADR links point to existing files under `docs/adr/`
30. ROADMAP.md phases are consistent with README.md
31. API.md endpoint list matches README.md planned API mentions
32. No broken links between documents

### T08 -- ADR-0002 (F02-T08)

33. ADR-0002 follows the same section structure as ADR-0001
34. ADR-0002 status is "proposed"
35. DECISIONS.md table includes ADR-0002 with "proposed" status
36. No contradictions between ADR-0002 and API.md

### T09 -- README.md update + diagrams (F02-T09)

37. Every doc link in README.md Documentation table resolves to an existing file
38. F02-architecture.mmd is valid Mermaid (no syntax errors)
39. F02-journey.mmd is valid Mermaid (no syntax errors)
40. README.md "Shipped" section includes both F01 and F02
41. "Clone to Run" commands reference existing scripts and make targets
42. README.md renders correctly (no broken markdown)

---

## 6. Anotacoes para tasks

No task annotations are being applied. Since F02 is shipped and this is a retroactive review, editing task files to append `**Test plan:** ver F02-test-plan.md (fixtures: ...)` would be cosmetic -- no downstream Developer or QA agent will consume these annotations for F02 work.

For the record, had TEA run before implementation:

| Task | Fixtures | Notes |
|------|----------|-------|
| F02-T01 | _(none)_ | Manual validation only: make targets, exit codes |
| F02-T02 | _(none)_ | Manual validation: platform-specific, not automatable in unit tests |
| F02-T03 | _(none)_ | Path validation script could automate scenarios 12-13 |
| F02-T04 | _(none)_ | Cross-reference validation (grep make targets) |
| F02-T05 | _(none)_ | Schema drift detection (compare models.py vs DATABASE.md) |
| F02-T06 | _(none)_ | Cross-reference validation |
| F02-T07 | _(none)_ | Link validation |
| F02-T08 | _(none)_ | Format consistency check |
| F02-T09 | _(none)_ | Link validation + Mermaid syntax check |

---

## 7. Gaps and risks for QA

1. **No automated doc-drift detection.** All 42 test scenarios above are manual. A future feature could introduce a CI step that validates: (a) all `src/` paths referenced in docs exist, (b) all cross-links between Markdown files resolve, (c) Mermaid files parse without errors. This would catch docs going stale as code evolves.

2. **Bootstrap scripts tested on limited platforms.** T02 scenarios 7-11 are inherently platform-dependent. Without CI runners on Mac and multiple Linux distros, coverage relies on manual testing by the developer. Acceptable for a solo project but a risk as contributors join.

3. **DATABASE.md schema drift.** Scenario 20-21 (column types match models.py) will silently go stale when F03+ adds new models or columns. A test that parses DATABASE.md table definitions and compares against SQLAlchemy model introspection would prevent this.

4. **Existing 27 tests are F01 scope.** F02 added no tests of its own. This is correct for a docs feature, but means test count did not grow. The regression gate (`make test` passing) is the only automated validation F02 contributes.

# QA Report -- F02: Project Reproducibility & Living Documentation

**Date:** 2026-08-18
**Verdict:** PASS

## Validation Results

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | Makefile -- `make help` works | PASS | `make` not installed in MINGW64 env, but the Makefile exists and the `help` target logic was verified by running its grep+awk pattern directly. Output lists 8 targets: help, setup, test, lint, format, clean, run-backfill, run-update. |
| 2 | Makefile -- `make test` runs 27+ tests green | PASS | Ran `.venv/Scripts/python.exe -m pytest tests/ -v` (the command behind `make test`). 27 tests collected, 27 passed in 1.48s. |
| 3 | Makefile -- `make lint` runs | PASS | Ran `.venv/Scripts/ruff.exe check src/ tests/` (the command behind `make lint`). Ruff executes successfully. 10 pre-existing lint errors (unused imports from F01 code + 1 line-length); these are NOT regressions introduced by F02. |
| 4 | pyproject.toml -- has [build-system], classifiers, URLs, license, readme | PASS | `[build-system]` with setuptools+wheel, 7 classifiers, `[project.urls]` with Homepage/Repository/Issues, `license = {text = "MIT"}`, `readme = "README.md"`. |
| 5 | .env.example -- documents DATABASE_URL, REQUEST_DELAY, HISTORY_DAYS, LOG_LEVEL | PASS | All 4 variables present with default values and descriptive comments. |
| 6 | .gitignore -- includes .env and .venv/ | PASS | Both `.env` and `.venv/` are listed, along with other standard entries (tcg_market.db, __pycache__, etc.). |
| 7 | Bootstrap scripts -- both exist, are executable, use set -euo pipefail | PASS | `bin/bootstrap-mac.sh` (132 lines) and `bin/bootstrap-linux.sh` (157 lines) both exist, have `-rwxr-xr-x` permissions, and start with `set -euo pipefail`. Both handle Python version detection, system deps, .env creation, and call `make setup`. |
| 8 | 11 doc files -- all exist under docs/, each has substantive content | PASS | All 11 files confirmed: ARCHITECTURE.md (249 lines), SETUP.md (136), DEVELOPMENT.md (153), DATA_SOURCES.md (183), DATABASE.md (272), API.md (173), ROADMAP.md (97), DECISIONS.md (27), SECURITY.md (76), CONTRIBUTING.md (91), AI_CONTEXT.md (131). None are stubs. |
| 9 | Cross-links -- links between docs resolve to real files | PASS | Spot-checked 14 cross-links across 8 files (ROADMAP->API, CONTRIBUTING->SETUP/DEVELOPMENT/SECURITY, DATABASE->DATA_SOURCES, ADR-0002->API, AI_CONTEXT->ARCHITECTURE/SECURITY, etc.). All reference files that exist at the expected relative path. |
| 10 | ADR-0002 -- exists, status "proposed", follows ADR-0001 format | PASS | `docs/adr/0002-web-stack-decision.md` exists with `Status: proposed`. Follows the same structure as ADR-0001: Status/Date/Deciders header, Context, Decision, Consequences (Easier/Harder), Alternatives considered. Substantive content (111 lines) covering FastAPI rationale with Flask/DRF/Litestar/raw-ASGI alternatives. |
| 11 | README.md -- has Clone to Run section, Documentation table, F02 in Shipped | PASS | "Clone to Run" section with copy-paste commands (lines 6-22). "Documentation" table with all 11 docs linked (lines 136-151). "Shipped" section includes F02 entry (lines 173-181). |
| 12 | Diagrams -- F02-architecture.mmd and F02-journey.mmd exist with valid Mermaid | PASS | Both files exist under `docs/diagrams/`. `F02-architecture.mmd` is a `flowchart TB` showing project root files, bootstrap scripts, docs, ADRs, and diagrams with relationships. `F02-journey.mmd` is a `flowchart TD` showing the new-contributor onboarding flow from clone through bootstrap, test, and first backfill. Both use valid Mermaid syntax. |
| 13 | No regressions -- all existing tests still pass | PASS | Full test suite: 27/27 passed (1.48s). No test failures or warnings. |

## Summary

All 13 validation checks pass. The feature delivers:

- A complete Makefile with 8 documented targets
- Proper pyproject.toml metadata (build-system, classifiers, URLs, license)
- Environment variable documentation via .env.example
- Two robust bootstrap scripts (Mac/Linux) with proper error handling
- 11 substantive documentation files with working cross-links
- ADR-0002 recording the FastAPI web stack decision
- Updated README with Clone-to-Run, documentation index, and F02 in Shipped
- Two valid Mermaid diagrams for F02

### Minor Observation (non-blocking)

Ruff reports 10 lint errors in pre-existing F01 code (9 unused imports, 1 line-length violation). These are not F02 regressions and do not block this feature, but should be cleaned up in a future pass.

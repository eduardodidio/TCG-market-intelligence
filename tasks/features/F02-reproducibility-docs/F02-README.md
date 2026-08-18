# F02 -- Project Reproducibility & Living Documentation

**Status:** done
**Created:** 2026-08-18
**Owner:** Eduardo Rutkoski Didio

## Objective

Make the project fully reproducible from a fresh clone (Makefile, .env.example,
complete pyproject.toml, bootstrap scripts for Mac/Linux) and establish a living
documentation tree that stays in sync with code as features ship. Record the
web-stack decision as ADR-0002.

## Context

After F01 shipped the MYP Cards collector MVP, the project lacks:

1. **Reproducibility** -- no Makefile, no .env.example, pyproject.toml missing
   build-system/URLs/classifiers, no bootstrap script for new contributors.
2. **Living docs** -- only README.md and one ADR exist. The project needs
   architecture docs, data-source docs, database schema docs, setup guide,
   development guide, security policy, contribution guide, roadmap, and
   AI context file.
3. **ADR gap** -- the eventual web stack (FastAPI vs Flask vs ...) needs an
   ADR before any API work begins.

## Tasks

| Wave | Task   | Type  | Description                                           | Status  |
|------|--------|-------|-------------------------------------------------------|---------|
| 0    | F02-T01 | setup | Makefile + .env.example + pyproject.toml completion   | planned |
| 0    | F02-T02 | setup | Bootstrap scripts for Mac and Linux                   | planned |
| 1    | F02-T03 | docs  | ARCHITECTURE.md                                       | planned |
| 1    | F02-T04 | docs  | SETUP.md + DEVELOPMENT.md                             | planned |
| 1    | F02-T05 | docs  | DATA_SOURCES.md + DATABASE.md                         | planned |
| 1    | F02-T06 | docs  | SECURITY.md + CONTRIBUTING.md + AI_CONTEXT.md         | planned |
| 1    | F02-T07 | docs  | API.md + ROADMAP.md + DECISIONS.md                    | planned |
| 2    | F02-T08 | docs  | ADR-0002: Web stack decision                          | planned |
| 2    | F02-T09 | docs  | README.md update + F02 diagrams                       | planned |

## Waves

- **Wave 0 (Setup):** T01, T02 -- build tooling and bootstrap scripts
- **Wave 1 (Docs, parallel):** T03, T04, T05, T06, T07 -- all doc files, no
  inter-dependencies
- **Wave 2 (Finalize):** T08, T09 -- ADR depends on ARCHITECTURE.md context;
  README update and diagrams depend on all docs being written

## Sharding

Sharding is **enabled** (9 tasks >= threshold of 6). Each task file is a
self-contained brief. Developer agents receive individual task files, not this
manifest.

## Acceptance Criteria

- **AC1:** `make setup` on a fresh clone installs deps and creates the DB
- **AC2:** `make test` runs the full test suite
- **AC3:** `make lint` runs ruff
- **AC4:** `.env.example` documents all environment variables
- **AC5:** `pyproject.toml` has build-system, project URLs, classifiers
- **AC6:** Bootstrap scripts work on Mac (Homebrew) and Linux (apt)
- **AC7:** All 11 doc files exist under `docs/` and are cross-linked
- **AC8:** ADR-0002 exists and records the web-stack decision
- **AC9:** README.md has a "Clone to Run" section with copy-paste commands
- **AC10:** F02-architecture.mmd and F02-journey.mmd exist under `docs/diagrams/`

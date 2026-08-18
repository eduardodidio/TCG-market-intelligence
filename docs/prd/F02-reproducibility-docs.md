# PRD: F02 - Project Reproducibility & Living Documentation

**Status:** Delivered
**Date:** 2026-08-18
**Author:** Eduardo Rutkoski Didio

## Problem

After F01 shipped the MYP Cards collector MVP, the project was not
reproducible from a fresh clone. There was no Makefile, no `.env.example`,
`pyproject.toml` was missing build-system metadata and project URLs, and
there were no bootstrap scripts for new contributors. Documentation was
limited to a single README.md and one ADR -- the project lacked
architecture docs, data-source docs, database schema docs, setup guides,
development guides, security policy, contribution guide, roadmap, and
AI context file. Additionally, the eventual web-stack decision needed an
ADR before any API work could begin.

## Goals

1. Add a `Makefile` with `setup`, `test`, and `lint` targets for one-command workflows
2. Create `.env.example` documenting all environment variables
3. Complete `pyproject.toml` with build-system, project URLs, and classifiers
4. Provide bootstrap scripts for Mac (Homebrew) and Linux (apt)
5. Create 11 living documentation files under `docs/` (ARCHITECTURE, SETUP,
   DEVELOPMENT, DATA_SOURCES, DATABASE, SECURITY, CONTRIBUTING, AI_CONTEXT,
   API, ROADMAP, DECISIONS) with cross-linking
6. Record the web-stack decision as ADR-0002
7. Update README.md with a "Clone to Run" section
8. Create F02 architecture and journey diagrams

## Non-Goals (this phase)

- CI/CD pipeline setup
- Deployment automation or infrastructure
- Automated doc generation from code (e.g., Sphinx, MkDocs)
- Hosting documentation externally

## Acceptance Criteria

1. **AC1:** `make setup` on a fresh clone installs deps and creates the DB
2. **AC2:** `make test` runs the full test suite
3. **AC3:** `make lint` runs ruff
4. **AC4:** `.env.example` documents all environment variables
5. **AC5:** `pyproject.toml` has build-system, project URLs, classifiers
6. **AC6:** Bootstrap scripts work on Mac (Homebrew) and Linux (apt)
7. **AC7:** All 11 doc files exist under `docs/` and are cross-linked
8. **AC8:** ADR-0002 exists and records the web-stack decision
9. **AC9:** README.md has a "Clone to Run" section with copy-paste commands
10. **AC10:** `F02-architecture.mmd` and `F02-journey.mmd` exist under `docs/diagrams/`

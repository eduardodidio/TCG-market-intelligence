# F02 -- Tech Lead Review

**Feature:** F02 -- Project Reproducibility & Living Documentation
**Reviewer:** Tech Lead agent
**Date:** 2026-08-18
**Verdict:** APPROVED_WITH_FOLLOWUP

---

## Summary

F02 delivers a comprehensive set of reproducibility tooling and living
documentation. The Makefile, bootstrap scripts, pyproject.toml completion,
.env.example, all 11 doc files, ADR-0002, and both Mermaid diagrams are
present and substantive. All 27 existing tests pass. The overall quality
is high -- the docs are well-written, practical, and correctly reflect the
codebase. Three broken cross-links and one placeholder need fixing via a
follow-up task.

---

## Acceptance Criteria Status

| AC | Description | Status | Notes |
|----|-------------|--------|-------|
| AC1 | `make setup` installs deps and creates DB | PASS | Makefile target correct; could not run `make` on Windows/MINGW64 but syntax is valid |
| AC2 | `make test` runs full test suite | PASS | Target invokes `pytest tests/ -v` correctly |
| AC3 | `make lint` runs ruff | PASS | Target invokes `ruff check src/ tests/` |
| AC4 | `.env.example` documents all env vars | PASS | DATABASE_URL, REQUEST_DELAY, HISTORY_DAYS, LOG_LEVEL all present |
| AC5 | `pyproject.toml` has build-system, URLs, classifiers | PASS | build-system (setuptools>=68, wheel), URLs (Homepage, Repo, Issues), classifiers (4 Python versions, 3-Alpha, MIT, Topic) |
| AC6 | Bootstrap scripts for Mac and Linux | PASS | Both executable, use `set -euo pipefail`, check Python>=3.11, copy .env, call `make setup` |
| AC7 | All 11 doc files exist and cross-linked | PARTIAL | All 11 files exist; 3 broken cross-links found (see below) |
| AC8 | ADR-0002 exists | PASS | Status "proposed", 4 alternatives considered, consequences documented |
| AC9 | README has "Clone to Run" section | PARTIAL | Section present but clone URL has `<owner>` placeholder |
| AC10 | F02 diagrams exist | PASS | Both F02-architecture.mmd and F02-journey.mmd present, valid Mermaid |

---

## Detailed Findings

### 1. Makefile (F02-T01)

**Architecture:** PASS
**Code quality:** PASS -- clean, follows the `##` help convention, all 8
targets present as specified.

Targets verified: help, setup, test, lint, format, clean, run-backfill,
run-update. The `clean` target uses `find ... -exec rm -rf {} +` which is
standard. The `run-backfill` target correctly uses `$(if ...)` for optional
SET and LIMIT parameters.

No issues found.

### 2. .env.example (F02-T01)

**Status:** PASS -- all four variables documented with sensible defaults
and comments.

### 3. pyproject.toml (F02-T01)

**Status:** PASS
- `[build-system]` with setuptools>=68 and wheel
- `license = {text = "MIT"}`
- `authors`, `readme`
- Classifiers: 3-Alpha, Python 3.11/3.12/3.13/3.14, Topic Database,
  Topic Games/Entertainment, MIT License
- `[project.urls]` with Homepage, Repository, Issues
- `[tool.ruff.lint]` select = ["E", "F", "I", "W"]

### 4. .gitignore (F02-T01)

**Status:** PASS -- `.env` and `.venv/` both present, along with other
standard entries (pycache, pytest_cache, egg-info, dist, build, db file).

### 5. Bootstrap Scripts (F02-T02)

**Status:** PASS
- Both use `set -euo pipefail`
- Both check Python >= 3.11 via version detection loop
- Both copy .env.example to .env if missing
- Both call `make setup`
- Both are executable (755)
- Linux script rejects running as root
- Mac script handles Homebrew installation
- Both are idempotent

### 6. ARCHITECTURE.md (F02-T03)

**Status:** PASS with minor note
- Layer diagram in Mermaid, all 6 layers documented
- Data flow explained step-by-step
- Extension points documented with code example
- Links to ADR-0001 in table

**MINOR:** The ADR table on line 235 only lists ADR-0001. Since ADR-0002
was delivered by T08 in a later wave, this table should be updated to
include it. The text on line 237 mentions ADR-0002 but as "future."

### 7. SETUP.md (F02-T04)

**Status:** PASS -- all required sections present (Prerequisites, Quick
Start Mac/Linux, Manual Setup, Verify, First Run, Troubleshooting).
References bootstrap scripts and make targets correctly.

### 8. DEVELOPMENT.md (F02-T04)

**Status:** ISSUE FOUND

**IMPORTANT -- Broken link (line 30):**
```
For a deeper architectural overview, see [ARCHITECTURE.md](./adr/) and the
```
The link text says "ARCHITECTURE.md" but the href points to `./adr/`
(a directory). Should be `[ARCHITECTURE.md](ARCHITECTURE.md)`.

All other content is correct: project structure, coding style (matches
pyproject.toml), testing conventions, linting, provider guide, commit
style, branch strategy, make targets table.

### 9. DATA_SOURCES.md (F02-T05)

**Status:** PASS -- thorough documentation of MYP Cards including
Cloudflare protection, URL patterns, data extraction methods, SKU format,
card names, rate limiting config, and known limitations. Cross-link to
DATABASE.md present.

### 10. DATABASE.md (F02-T05)

**Status:** PASS -- all 4 tables documented with columns, types, constraints,
and indexes. Mermaid ER diagram included. Idempotency strategy explained.
Migration strategy documented. Cross-links to DATA_SOURCES.md and source
files.

### 11. API.md (F02-T07)

**Status:** ISSUE FOUND

**IMPORTANT -- Broken link (line 172):**
```
[ADR-0002](adr/0002-web-stack-fastapi.md)
```
The actual file is `adr/0002-web-stack-decision.md`, not
`adr/0002-web-stack-fastapi.md`.

All other content is correct: clearly marked as NOT YET IMPLEMENTED,
all 8 planned endpoints documented, response format, pagination, error
codes.

### 12. ROADMAP.md (F02-T07)

**Status:** ISSUE FOUND

**IMPORTANT -- Broken link (line 96):**
```
See [CONTRIBUTING.md](../CONTRIBUTING.md)
```
Since ROADMAP.md is at `docs/ROADMAP.md`, `../CONTRIBUTING.md` resolves to
the project root. But CONTRIBUTING.md lives at `docs/CONTRIBUTING.md`.
Should be `[CONTRIBUTING.md](CONTRIBUTING.md)`.

All phases (1-8) are present and match the task specification.

### 13. DECISIONS.md (F02-T07)

**Status:** PASS -- ADR index table includes both ADR-0001 (accepted) and
ADR-0002 (proposed). "How to Add a Decision" references the template file,
which exists at `docs/adr/0000-template.md`.

### 14. SECURITY.md (F02-T06)

**Status:** PASS -- consistent with CLAUDE.md guardrails.

Cross-checked against CLAUDE.md "Guardrails de Seguranca":
- No force push: covered
- No --no-verify: covered
- No git reset --hard: covered
- No git add -A / git add .: covered
- No secrets in commits: covered
- No amend on shared branches: covered
- No rebase on shared branches: covered
- No disabling validation/auth/tests: covered
- No hardcoded secrets: covered
- Input validation at boundaries: covered (under Code Safety)
- No new deps without confirmation: covered
- No destructive ops without confirmation: covered
- No CI/CD changes without confirmation: covered

Adds Data Scraping Ethics section (appropriate for this project).
Vulnerability reporting process documented.

### 15. CONTRIBUTING.md (F02-T06)

**Status:** PASS -- links to SETUP.md, DEVELOPMENT.md, SECURITY.md.
Feature workflow, code style, PR guidelines, documentation requirements,
and testing expectations all covered.

### 16. AI_CONTEXT.md (F02-T06)

**Status:** PASS -- tech stack matches pyproject.toml, architecture summary
consistent with ARCHITECTURE.md, guardrails consistent with CLAUDE.md.
Common tasks section provides useful quick-reference commands.

### 17. ADR-0002 (F02-T08)

**Status:** PASS
- Follows ADR-0001 format (Status, Date, Deciders, Context, Decision,
  Consequences, Alternatives)
- Status is "proposed" (correct -- API not built yet)
- 4 alternatives considered (Flask, DRF, Litestar, raw ASGI)
- Consequences split into "Easier" and "Harder"
- Context links to API.md

### 18. README.md (F02-T09)

**Status:** PARTIAL

**MINOR -- Placeholder in Clone to Run (line 9):**
```
git clone https://github.com/<owner>/tcg-market-intelligence.git
```
The `<owner>` should be `eduardodidio` (used correctly in pyproject.toml
URLs and other docs like SETUP.md).

Positive findings:
- "Clone to Run" section present in correct position
- "Documentation" table lists all 11 docs with correct links
- "Shipped" section includes both F01 and F02
- Quick Start section now uses `make` targets
- "Running Tests" section still has old `pip install` command (line 131-132)
  but this is pre-existing, not introduced by F02

### 19. Diagrams (F02-T09)

**Status:** PASS
- `F02-architecture.mmd`: valid Mermaid flowchart showing project root
  files, bootstrap scripts, docs tree, ADR directory, diagrams directory,
  and their relationships
- `F02-journey.mmd`: valid Mermaid flowchart showing the new contributor
  journey from clone through bootstrap, test, explore docs, first backfill,
  to "ready to develop"

### 20. Test Suite

**Status:** PASS -- all 27 tests pass (verified via pytest run).

---

## Issues Summary

### IMPORTANT (should fix, approve with follow-up)

| # | File | Issue |
|---|------|-------|
| I1 | `docs/DEVELOPMENT.md:30` | Broken link: `[ARCHITECTURE.md](./adr/)` should be `[ARCHITECTURE.md](ARCHITECTURE.md)` |
| I2 | `docs/API.md:172` | Broken link: `adr/0002-web-stack-fastapi.md` should be `adr/0002-web-stack-decision.md` |
| I3 | `docs/ROADMAP.md:96` | Broken link: `../CONTRIBUTING.md` should be `CONTRIBUTING.md` (same directory) |

### MINOR (nice to have)

| # | File | Issue |
|---|------|-------|
| M1 | `README.md:9` | Placeholder `<owner>` in clone URL; should be `eduardodidio` |
| M2 | `docs/ARCHITECTURE.md:234` | ADR table only lists ADR-0001; should include ADR-0002 now that it exists |
| M3 | `README.md:131-132` | Pre-existing "Running Tests" section still shows `pip install pytest pytest-asyncio` instead of `make test` (not introduced by F02, but good cleanup opportunity) |

---

## Verdict: APPROVED_WITH_FOLLOWUP

The feature is well-executed. All acceptance criteria are substantially met.
The 11 documentation files are comprehensive, accurate, and practical. The
Makefile, bootstrap scripts, and pyproject.toml are correct. ADR-0002
follows the established format. Diagrams are valid Mermaid. Security policy
is consistent with CLAUDE.md guardrails. No tests are broken.

The three broken cross-links (I1, I2, I3) are not blocking because they
are easily fixable and do not affect the substance of the documentation.
They should be fixed in a quick follow-up commit before the next feature
begins.

---

## Retrospective Seeds

- **Pattern:** Cross-links between docs break when file names do not match
  exactly between the task spec and the implementation (e.g.,
  `0002-web-stack-fastapi.md` vs `0002-web-stack-decision.md`).
- **Role(s) affected:** developer
- **Lesson:** When Wave 2 tasks reference files created by earlier tasks,
  the developer should verify the actual filenames on disk rather than
  relying on the task spec's assumed filenames. A simple `ls` check after
  writing cross-links would catch this class of bug.

- **Pattern:** Relative link paths in docs are error-prone when all docs
  live in the same `docs/` directory but a developer uses `../` or `./adr/`
  instead of a simple filename.
- **Role(s) affected:** developer, techlead
- **Lesson:** For docs in the same directory, always use bare filenames
  (e.g., `ARCHITECTURE.md`, not `./ARCHITECTURE.md` or `../docs/ARCHITECTURE.md`).
  Tech lead should spot-check relative link paths in every docs-heavy feature.

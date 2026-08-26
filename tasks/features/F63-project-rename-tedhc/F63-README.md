# F63 — Project Rename to TEDHC Market

**Status:** shipped
**Created:** 2026-08-26
**Priority:** P3 (cosmetic / branding)
**Wave Group:** 0 (independent — parallel with F64, F68, F70)

## Summary

Rename the project internally from "TCG Market Intelligence" to "TEDHC Market"
(Trading Elder Dragon Highlander Cards). The full name is for internal/docs
registration only — the frontend sidebar/header keeps showing "TCG Market" (or
updates to "TEDHC Market" as a short brand). The expanded acronym should NOT
appear in the UI.

## Acceptance Criteria

1. FastAPI app title updated to "TEDHC Market API"
2. CLAUDE.md project name updated
3. README.md project title updated
4. Frontend sidebar/header shows "TEDHC Market" (short form only)
5. package.json (frontend) name field updated
6. No functional changes — pure branding/config

## Architecture Decisions

- Keep the git repo name as-is (TCG-market-intelligence) to avoid breaking links
- Internal docs reference "TEDHC Market (Trading Elder Dragon Highlander Cards)" once in README, then use short form
- No ADR needed — cosmetic change

## Waves

| Wave | Tasks | Description |
|------|-------|-------------|
| 0    | T01   | Update all project name references |

## Tasks

- **T01** (Wave 0): Update project name across config, docs, frontend

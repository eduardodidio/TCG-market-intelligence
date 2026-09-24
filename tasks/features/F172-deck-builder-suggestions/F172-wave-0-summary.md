# F172 — Wave 0 summary

**Status:** completed
**Tasks:** F172-T01
**Generated:** 2026-09-24T18:10:00Z

## Files touched
- `docs/prd/F172-deck-builder-suggestions.md` (T01: new PRD covering both modes, persistence table, API, daily routine, risks)
- `docs/adr/0015-deck-suggestion-queue-claude.md` (T01: new ADR — no Anthropic SDK/httpx+CLI, own-module table decisions)
- `src/deck_suggestions/__init__.py` (T01: package scaffold, empty)
- `frontend/src/components/decks/.gitkeep` (T01: placeholder, empty dir needed for Wave 1 components; removed by T06)
- `tests/unit/deck_suggestions/__init__.py` (T01: test package scaffold, empty)

## Decisions
- ADR 0015 confirmed free/unused before this task; reserved number honored as instructed.
- PRD additionally drew from `_brief/02-suggestion-persistence-api.md` (not explicitly cited in T01) since the data model/API table needed that content.

## Notes for next Wave
- `pytest-cov` is not installed in this environment; plain `pytest` fails on the `--cov…` addopts in `pyproject.toml`. Wave 1 tasks should run tests with `-o addopts=""` or install `pytest-cov` if they need coverage locally.
- `frontend/src/components/decks/.gitkeep` exists only to keep the empty dir tracked — T06 will delete it once real components land there, no action needed before then.
- Branch is `wt/F172` (a worktree branch off `homol`, not `main`) — safe for Wave 1 commits per gitflow rules.

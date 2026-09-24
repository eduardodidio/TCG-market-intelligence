# F176 — Wave 4 summary

**Status:** completed (uncommitted — pending review/commit)
**Tasks:** F176-T11, F176-T12
**Generated:** 2026-09-24T00:00:00Z (approximate, from session clock)

## Files touched
- `src/cli/main.py` (T11: `--dry-run` flag added to `backfill_snapshots_cmd`, count-only message, no other command touched)
- `bats/daily-snapshot.bat` (T11: new, mirrors `process-queue.bat` format, calls `python -m src.cli.main daily-snapshot`; must be added with `git add -f`, `bats/` is gitignored)
- `README.md` (T11: `## Commands` entries for `daily-snapshot`/`backfill-snapshots --dry-run`/the new `.bat`; new `### F176 -- Collection Price History` note appended at end of `## Shipped`)
- `tests/test_cli_snapshot.py` (T11: new cases for `--dry-run`, `--days 0` error, `.bat` content check)
- `tests/integration/test_collection_price_history.py` (T12: new, 6 test classes — `TestNormalCardHistory`, `TestFoilCardHistory`, `TestDailyRecording`, `TestCrossEndpointConsistency`, `TestHistoryEdgeCases`, `TestRegressionGuards`; 19 tests, ~5-6s isolated run, green)

## Decisions
- T12 used direct historical-observation inserts instead of `freezegun` (not a project dependency, confirmed via `grep freezegun pyproject.toml`), running the sweep only for "today" per the Dev Notes fallback.
- README F176 note appended at the *end* of `## Shipped` (not inline) to minimize merge conflicts with other F171-F179 tasks touching the same file.

## Notes for next Wave
- No Wave 5 exists — this is the last Wave for F176. Remaining work is: full `pytest tests/ --cov=src` + `ruff check src/` sweep, TechLead review, QA, and the **pending-user** AC15 validation on `homol` with real Neon data before promotion to `main`.
- T12 flags a pre-existing quirk: `get_cards_for_liga_scan` reads `UserCollectionRow.name_en`/`name_pt` (not `CardRow.name_en`) to build the Liga search name — collection fixtures must set names on the collection row, not just the card row.
- T12's AC "full suite green" is unmet as noted by the developer: 79-112 pre-existing failing tests unrelated to F176, not introduced by this task — TechLead/QA should verify this claim rather than block on it blindly.
- Working tree changes for Wave 4 are not yet committed (git status shows modifications/untracked files); a commit step is still needed before TechLead review can diff a clean Wave 4 changeset.

DIDIO_DONE: techlead wrote F176-wave-4-summary.md

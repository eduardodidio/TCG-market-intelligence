# F171 — Wave 5 summary

**Status:** completed (uncommitted — pending `git add`/commit on `homol`)
**Tasks:** F171-T13, F171-T14
**Generated:** 2026-09-24T00:00:00Z

## Files touched
- `src/cli/main.py` (T13: `import-csv` gets `--currency auto|BRL|USD`, replaces the hardcoded Liga dry-run path with `import_collection_csv(..., dry_run=True)`, wires `rate_lookup_from_converter(CurrencyConverter(Repository(db)))` for the real run)
- `tests/cli/test_import_csv_currency.py` (T13: new, 7 tests — happy BRL/USD dry runs, `--currency usd` lower-case override, invalid `EUR` choice → exit code 2, `n` at confirm → Aborted/no writes, Liga no-price boundary)
- `docs/adr/0014-import-currency-normalization.md` (T14: new, Status: Accepted — storage-currency decision, PTAX-at-boundary, drop-not-guess on missing rate, rejected alternatives)
- `README.md` (T14: additive-only append, `### F171 — Import respecting the file currency` section)
- `docs/diagrams/F171-journey.mmd` (T14: synced, +12 lines)

## Decisions
- T14 confirmed ADR number **0014** as reserved (no collision) — used as-is, no bump needed.
- `docs/diagrams/F171-architecture.mmd` needed no changes (already matched shipped code); only the journey diagram drifted.

## Notes for next Wave
- Nothing pending inside F171 — this was the last wave. All Wave 5 changes are **uncommitted** in the working tree (`README.md`, `docs/diagrams/F171-journey.mmd`, `src/cli/main.py` modified; `docs/adr/0014-import-currency-normalization.md`, `tests/cli/test_import_csv_currency.py` untracked).
- Targeted run of `tests/cli/test_import_csv_currency.py` passes (7 passed); `ruff check src/cli/main.py` is clean. The full-suite gate (`pytest tests/ --cov=src`, `cd frontend && npm test && npm run build`) from T14's acceptance criteria was **not** re-run in this summary pass — TechLead/QA should run it before sign-off.
- README diff verified additive-only (`git diff README.md` shows 0 removed lines), satisfying AC10's boundary check.

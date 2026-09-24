# F171 — Wave 4 summary

**Status:** completed
**Tasks:** F171-T10
**Generated:** 2026-09-24T13:22:40Z

## Files touched
- `src/api/routers/collection.py` (T10: `import_collection` now accepts `currency`/`dry_run` query params + `converter` dep, forwards them to `import_collection_csv`, skips canonize scheduling on dry_run)
- `src/api/schemas/collection.py` (T10: `ImportResult` extended with `detected_currency`, `currency_source`, `currency_confidence`, `currency_evidence`, `priced`, `converted`, `exchange_rate`, `price_warnings`, `dry_run` — all optional/defaulted, backward compatible)
- `tests/api/test_collection_import_currency.py` (T10: new, covers BRL/USD upload, `?currency=` override, `?currency=EUR` 422, `?dry_run=true` no-write path)

## Decisions
- No deviations from the T10 spec; `converter` wired via `get_currency_converter_dep` + `rate_lookup_from_converter` exactly as T07/T08 established in Wave 3.
- Changes are uncommitted in the working tree as of this summary (not yet part of a `F171 Wave 4` commit).

## Notes for next Wave
- `pytest tests/api/test_collection_import_currency.py tests/api/test_collection_import_canonize.py -q` → 14 passed; no regressions to the existing canonize import tests.
- T13 (CLI `import-csv --currency`, Wave 5) depends on T07+T09 (both done in Wave 3), not directly on T10 — no blocking contract change from this wave.
- T14 (docs/ADR/README sync, Wave 5) should reference the final `ImportResult` field set above when documenting the `/collection/import` response.
- Working tree still has these T10 changes unstaged/uncommitted — commit per CLAUDE.md rules (stage file by file, no `git add -A`) before promoting.

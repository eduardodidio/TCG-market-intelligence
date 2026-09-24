# F171 — Wave 1 summary

**Status:** completed
**Tasks:** F171-T02, F171-T03, F171-T11
**Generated:** 2026-09-24T12:50:00Z

## Files touched
- `src/currency/money.py` (T02: `detect_symbol`, `parse_money`, `number_format_hint` — pure, stdlib only)
- `tests/currency/test_money.py` (T02: parametrized cases)
- `src/currency/import_conversion.py` (T03: USD→BRL conversion at import boundary using PTAX)
- `tests/currency/test_import_conversion.py` (T03)
- `frontend/src/components/CsvImportModal.tsx` (T11: `detecting`/`detected` states, Auto/BRL/USD selector, low-confidence warning, priced/converted summary)
- `frontend/src/api/collection.ts` (T11: `importCollectionCsv` now accepts `{ currency, dryRun }`, kept backward-compatible signature)
- `frontend/src/types/api.ts` (T11: `ImportResult` extended with detection/conversion fields)
- `frontend/src/i18n/locales/pt-BR.json`, `frontend/src/i18n/locales/en.json` (T11: new `importCsv*` and `purchases.convertedFrom` keys, identical key sets, no-accent pt-BR style kept)
- `frontend/src/components/__tests__/CsvImportModal.test.tsx` (T11: new, 10 tests)

## Decisions
- T11 coded against the documented `/collection/import` dry-run contract only, since the backend (T10) ships in Wave 4 — no coupling introduced.
- _none_ (no other direction changes)

## Notes for next Wave
- Backend suite: `pytest tests/currency/ -q` → **75 passed**. Frontend: `npx vitest run CsvImportModal.test.tsx` → **10 passed**. Nothing committed yet — Wave 0 and Wave 1 files are still untracked/unstaged; confirm commit strategy before Wave 2 starts touching the same files.
- **Data point for Wave 2 (T04/T05):** `F171-T02.md` and the on-disk `money.py`/`test_money.py` are done and tests pass, but the task file header still reads `Status: planned` — Wave 2 devs should update it to `done` when they pick up T02's output, since T04/T05 depend on it.
- `CurrencyDetection` shape from Wave 0 (`.evidence`, `.unsupported_symbols` as `list[str]`) was reused as-is by T02/T03/T11 — no reinvention.

DIDIO_DONE: techlead wrote F171-wave-1-summary.md

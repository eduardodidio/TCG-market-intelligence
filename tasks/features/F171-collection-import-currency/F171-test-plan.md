# F171 — Test Plan

- **status:** drafted
- **generator:** TEA
- **generated-at:** 2026-09-24
- **source-brief:** `tasks/features/F171-collection-import-currency/_brief/00-overview.md`

## 1. Fixtures

| Fixture | Path | Domain | Owner |
|---|---|---|---|
| `liga_brl_no_price.csv` (Liga header + 3 rows, **cp1252**, accented name e.g. `Irmãos`, no price column) | `tests/fixtures/collection_import/liga_brl_no_price.csv` | csv/currency | F171-T01 |
| `liga_brl_with_price.csv` (Liga header + `Preco (R$)` column, `12,50` / `1.234,56` / `0,75`) | `tests/fixtures/collection_import/liga_brl_with_price.csv` | csv/currency | F171-T01 |
| `generic_brl_symbol.csv` (`Name,Set code,Collector number,Quantity,Price`, `R$ 10,00` / `R$ 2,50` / `R$ 1.050,00`) | `tests/fixtures/collection_import/generic_brl_symbol.csv` | csv/currency | F171-T01 |
| `generic_usd_symbol.csv` (same columns, `US$ 2.00` / `$0.50` / `$1,050.00`) | `tests/fixtures/collection_import/generic_usd_symbol.csv` | csv/currency | F171-T01 |
| `manabox_usd.csv` (ManaBox header incl. `Purchase price currency=USD`, `2.00` / `0.35`) | `tests/fixtures/collection_import/manabox_usd.csv` | csv/currency | F171-T01 |
| `manabox_brl.csv` (ManaBox header, `Purchase price currency=BRL`, dot-decimal `10.50` / `1.75`) | `tests/fixtures/collection_import/manabox_brl.csv` | csv/currency | F171-T01 |
| `ambiguous_no_hint.csv` (generic header, prices `10` / `3`, no symbol/separator → must default BRL) | `tests/fixtures/collection_import/ambiguous_no_hint.csv` | csv/currency | F171-T01 |
| `purchase_usd_sample.html` (minimal Liga-order-style markup, one item `US$ 3.10`, one `R$ 9,75`) | `tests/fixtures/purchase_usd_sample.html` | purchases | F171-T01 |
| `_fake_rate_lookup` (lambda / `RateLookup` stub returning a fixed `Decimal`, e.g. `Decimal("5.40")`, sometimes `None`) | inline in `tests/currency/test_import_conversion.py`, `tests/collection/test_importer_currency.py`, `tests/api/test_purchases_currency.py`, `tests/api/test_collection_import_currency.py`, `tests/api/test_collection_batch_currency.py`, `tests/cli/test_import_csv_currency.py` | currency/api/cli | F171-T03 (pattern), reused by T07/T08/T09/T10/T13 |
| `_stub_currency_converter_dep` (FastAPI dependency override for `get_currency_converter_dep`, `get_display_rate` returns a fixed rate or `None`) | inline in `tests/api/test_collection_import_currency.py`, `tests/api/test_collection_batch_currency.py` | api | F171-T10 (pattern), reused by T09 |
| `mockImportCollectionCsv` (mock of `importCollectionCsv` distinguishing `dryRun: true` vs the real call, returning a `CurrencyDetection`-shaped `ImportResult`) | `frontend/src/components/__tests__/CsvImportModal.test.tsx` | frontend | F171-T11 |
| `mockPurchasePreviewWithConversion` (mock preview response with one converted USD match and one BRL match) | `frontend/src/pages/__tests__/ImportPurchasesPage.test.tsx` | frontend | F171-T12 |

Only the 7 CSV files + 1 HTML file are static fixture files (all created by T01, shared by
downstream tasks); everything else is a builder (lambda/Mock/`vi.mock`) inline in the test file
that uses it, following the existing repo pattern (`tests/collection/test_importer_transaction.py`,
`tests/api/test_import_purchases.py`). Per `feedback_no_ceremony_specs.md`, no separate shared
fixture module is introduced beyond the T01 files — the currency logic is exercised by many small,
task-local stubs, and a shared fixture module here would only add indirection since each task's
stub shape (rate present/absent, per-row vs per-file) differs.

## 2. Harnesses por fronteira

### Unit
- **Framework:** pytest (backend, pure functions) / none needed on the frontend for pure logic (there is no pure TS unit under this feature — the frontend work is all component-level).
- **Comando:** `pytest tests/currency/test_money.py tests/currency/test_import_conversion.py tests/collection/test_csv_columns.py tests/collection/test_batch_parser.py tests/services/test_purchase_parser.py -v`
- **Path padrão:** `tests/currency/*.py`, `tests/collection/test_csv_columns.py`, `tests/collection/test_batch_parser.py`, `tests/services/test_purchase_parser.py`

### Integration
- **Framework:** pytest + tmp/in-memory SQLite engine (pattern from `tests/collection/test_importer_transaction.py`) for T07/T09/T13; pytest + FastAPI `TestClient` with `app.dependency_overrides` (pattern from `tests/api/test_import_purchases.py`) for T08/T09/T10; Vitest + React Testing Library with mocked API module (pattern from `frontend/src/pages/__tests__/ImportPurchasesPage.test.tsx`) for T11/T12.
- **Comando (backend):** `pytest tests/collection/test_importer_currency.py tests/api/test_purchases_currency.py tests/api/test_collection_batch_currency.py tests/api/test_collection_import_currency.py tests/cli/test_import_csv_currency.py -v`
- **Comando (frontend):** `cd frontend && npx vitest run src/components/__tests__/CsvImportModal.test.tsx src/pages/__tests__/ImportPurchasesPage.test.tsx`
- **Path padrão:** `tests/collection/test_importer_currency.py`, `tests/api/test_*_currency.py`, `tests/cli/test_import_csv_currency.py`, `frontend/src/**/__tests__/*.test.tsx`

### E2E
- **N/A.** The project has no browser-level E2E harness (Playwright is used only by the Liga Magic
  provider for scraping, not for frontend flows — same conclusion as F175). The full user journey
  (select file → dry-run detect → confirm/override currency → import) is covered end-to-end at the
  API layer by T10's `TestClient` tests plus the CLI's `CliRunner` tests (T13), and at the UI layer
  by T11's component tests with a mocked API — that combination is the project's existing substitute
  for browser E2E and is sufficient for a currency-detection bug fix.

## 3. Perf budgets

_Sem perf budgets aplicáveis._ This feature is a correctness fix (currency detection/conversion),
not a performance-sensitive path: CSV files are small (imports are already bounded to a user's own
collection size, unchanged from the current importer), and the only new bounded work is the "sample
at most 200 non-empty price cells" rule in `detect_file_currency` (T04), which is a correctness
boundary (tested in scenario T04-Boundary below), not a latency budget.

## 4. Mocks vs hits real

| Componente | Decisão | Justificativa |
|---|---|---|
| `parse_money` / `detect_symbol` / `number_format_hint` / `to_brl` (T02, T03) | real | Pure functions with no I/O — the whole point of the test is the parsing/conversion logic itself; mocking would defeat the test. |
| `resolve_columns` / `detect_file_currency` (T04) | real, against the T01 CSV fixtures read from disk | The detection precedence chain is exactly what's under test; reading the real fixture files (including the real cp1252 file) is the only way to catch encoding and header-matching bugs, and the cost is negligible (small files, no network). |
| SQLite engine in `test_importer_currency.py` (T07) and `test_import_csv_currency.py` (T13) | real (tmp/in-memory, existing project pattern) | Matches `test_importer_transaction.py`; the behavior under test (rows written, `acquisition_price` stored value) is a DB side effect that a mocked session would hide. |
| `rate_lookup` passed into `to_brl`/`import_collection_csv`/`batch_add_entries` (T03, T07, T09, T13) | mock (fake lambda or `Mock`) | The PTAX rate itself comes from `CurrencyConverter.get_closest_rate`, already covered elsewhere; a fixed fake rate (`Decimal("5.40")`) makes the conversion math deterministic without seeding real `exchange_rates` rows in every test. `feedback_no_ceremony_specs.md`: seeding real rate rows for every currency test would be pure ceremony — the conversion logic doesn't care where the rate came from. |
| `CurrencyConverter.get_display_rate` in API tests (T08, T09, T10) | mock (patched or dependency-overridden) | Same reasoning as above, applied via FastAPI's existing `dependency_overrides` mechanism (already the project's pattern in `test_import_purchases.py`), so no real Neon/SQLite rate data is needed to test the router glue. |
| `Repository` / DB in `test_import_csv_currency.py` (T13, CLI) | real (tmp SQLite via `create_engine`) for the dry run and the real import; `CurrencyConverter.get_display_rate` mocked/patched for the rate | Dry run must prove it does not write — that requires a real (tmp) engine, not a mock session. The rate itself is faked for determinism, consistent with the API tests. |
| `importCollectionCsv` (frontend, T11) | mock (`vi.mock`) | Component test, not a network integration test; the existing pattern in the codebase (`ImportPurchasesPage.test.tsx`) mocks the API module so the test asserts UI state transitions, not fetch plumbing. |
| Purchase preview API (frontend, T12) | mock (`vi.mock`) | Same reasoning; T12 only renders a badge from response fields it does not control the shape of end-to-end. |

## 5. Test scenarios resumo

1. `parse_money("R$ 1.234,56") == (Decimal("1234.56"), "BRL")`; `parse_money("US$ 1,234.56") == (Decimal("1234.56"), "USD")`; `parse_money("$0.50") == (Decimal("0.50"), "USD")` — **F171-T02**.
2. `parse_money("12,50")` and `parse_money("12.50")` both → `(Decimal("12.50"), None)` — **F171-T02**.
3. Ambiguous `1.234` / `1,234` resolved per the documented `hint` rule (BRL hint → thousands; USD/None hint → decimal) — **F171-T02**.
4. `parse_money("")`, `None`, `"abc"`, `"-5"`, `"1e5"` → amount `None`, no exception — **F171-T02**.
5. `detect_symbol("€ 3,00") == "EUR"`; NBSP between symbol and number; lower-case `r$`; `(unid.)` suffix stripped — **F171-T02**.
6. Boundary: `0,00` → `0.00`; `1000000,00` valid; `1000000,01` → `None`; half-up rounding `0,005` → `0.01` — **F171-T02**.
7. `number_format_hint`: `12,50`→BRL, `1.234,56`→BRL, `12.50`→USD, `1,234.56`→USD, `12`→None — **F171-T02**. 100% line coverage of `money.py` required.
8. `to_brl(Decimal("2.00"), "USD", d, lambda _: Decimal("5.40")).brl == Decimal("10.80")`; BRL passthrough with `rate is None` — **F171-T03**.
9. No rate (`None`, `0`, negative) → `brl is None`, `warning == "no_rate"`, never the raw USD amount — **F171-T03**.
10. `EUR` (or any unsupported currency) → `warning == "unsupported_currency"` — **F171-T03**.
11. Rounding: `0.335 USD × 5.00` → `1.68` HALF_UP; `on_date` is passed through to the rate lookup (assert mock call arg) — **F171-T03**. 100% coverage of `import_conversion.py` required.
12. `resolve_columns`: all 13 Liga headers resolve, `origin == "liga"`; ManaBox fixtures → `origin == "manabox"`; BOM on the first header; extra spaces; upper-case `PREÇO` — **F171-T04**.
13. `detect_file_currency` per fixture: `manabox_brl.csv` → BRL from the currency column despite dot-decimal numbers; `generic_usd_symbol.csv`/`generic_brl_symbol.csv` → symbol source; `liga_brl_with_price.csv` → header source; `liga_brl_no_price.csv` → origin source; `ambiguous_no_hint.csv` → default source, confidence low — **F171-T04**.
14. `choice="USD"` on a BRL file → USD/`user` (override wins) — **F171-T04**.
15. Mixed 3×`R$` + 1×`US$` in the sample → BRL, confidence low, evidence mentions "mixed"; a currency column containing only `EUR` → `unsupported_symbols` has `EUR` and detection falls through — **F171-T04**.
16. Empty header list → `ColumnMap(fields={}, origin="generic")`, no exception; empty price cells → falls through to origin/default; 250 price rows → only 200 sampled (assert via evidence counts) — **F171-T04**. ≥95% coverage of `csv_columns.py` required.
17. `parse_brl_price("R$ 1.234,56") == Decimal("1234.56")` (legacy) and `parse_brl_price("12.50") == Decimal("12.50")` (the 1250 bug is fixed) — **F171-T05**.
18. `parse_price_with_currency("US$ 3.10") == (Decimal("3.10"), "USD")`; items parsed from `purchase_usd_sample.html` carry `currency` USD and BRL respectively — **F171-T05**.
19. Garbage input (`"—"`) → `Decimal("0")`, no exception (legacy contract preserved); all pre-existing `test_purchase_parser.py` cases still pass unchanged — **F171-T05**.
20. Batch line `2 Lightning Bolt [m10] NM R$12,50` → qty 2, name `Lightning Bolt`, set `m10`, quality NM, price `12.50` BRL — **F171-T06**.
21. `Sol Ring US$3.10` → price 3.10 USD; `Lightning Bolt @ 5,00` → price 5.00, currency `None`; a name with embedded digits (`Borrowing 100,000 Arrows`) is not misparsed as a price token (no symbol/`@` present) — **F171-T06**.
22. Two price tokens on one line → the last one wins; `R$abc` has no digit after the symbol → no match, name unaffected; `R$1.2.3,4,5` → `error == "Invalid price: ..."`; `R$1000000,01` → error (above the limit) — **F171-T06**. All pre-existing `test_batch_parser.py` cases still pass unchanged.
23. `import_collection_csv` on each BRL fixture (`generic_brl_symbol.csv`, `liga_brl_with_price.csv`, `manabox_brl.csv`) stores values unchanged (e.g. `10.50` stays `10.50`) — **F171-T07** (AC1).
24. `import_collection_csv` on each USD fixture (`generic_usd_symbol.csv`, `manabox_usd.csv`) with `rate_lookup` returning `5.40` stores `usd * 5.40` (e.g. `2.00` → `10.80`) — **F171-T07** (AC2).
25. `currency="BRL"|"USD"` override applies to every row, overriding per-row symbols/columns; `currency="USD"` on `generic_brl_symbol.csv` (e.g. `10,00`) stores `54.00` — **F171-T07** (AC3).
26. `ambiguous_no_hint.csv` → `currency_source == "default"`, values stored as BRL — **F171-T07** (AC4).
27. USD fixture with `rate_lookup=None` → `priced == 0`, a `no_rate` warning present, rows still imported (not dropped) — **F171-T07** (AC5).
28. `dry_run=True` writes nothing: row count in the DB is unchanged, existing collection rows are not deleted — **F171-T07** (AC8).
29. `liga_brl_no_price.csv` → identical result to pre-feature behavior, `acquisition_price` stays `None`, `priced == 0` — **F171-T07** (AC9, regression). All of `test_importer_canonize.py`, `test_importer_transaction.py`, `test_collection_import_canonize.py` still pass.
30. Edge/error: empty price cell → `None`, not counted as `priced`; quantity `""` → `1`, `"2.0"` → `2`; BOM in the header; invalid quantity `"abc"` → row skipped; unparseable price `"abc"` → price `None` + warning, row still imported; `EUR` symbol → `unsupported_currency` warning — **F171-T07**.
31. Boundary: 25 bad prices → `price_warnings` has 20 entries + `"... and 5 more"`; `dry_run` on a header-only CSV → all zeros — **F171-T07**.
32. Purchases preview: a USD item at `3.10` with a `5.00` rate → `unit_price == "15.50"`, `original_currency == "USD"`, `original_unit_price == "3.10"`; a BRL item is unchanged with `original_currency == "BRL"` and `exchange_rate` `None` — **F171-T08** (AC2, AC6).
33. Purchases preview: `order_date` `None` uses today's rate (assert the lookup call argument); no rate available → the item is excluded from `matches`, placed in `unmatched` with `reason="currency_conversion_failed"`, and a warning is added; `EUR` → `unsupported_currency` warning; `unit_price` `0` in USD → `"0.00"`, not an error — **F171-T08**. Existing `test_import_purchases.py` / `test_purchases_integration.py` still pass.
34. `POST /collection/batch/parse` with `Sol Ring US$3.10` returns `price "3.10"`, `price_currency "USD"` — **F171-T09** (AC7).
35. `POST /collection/batch` with `acquisition_price 3.10`, `price_currency USD`, rate `5.00` → stored `15.50`; BRL or `None` currency stored unchanged; no rate → row added with price `None` plus a warning; negative price → `422`; `price_currency "EUR"` → `422`; old payloads without the new fields behave exactly as before — **F171-T09**.
36. `POST /collection/import` on `generic_usd_symbol.csv` → `detected_currency "USD"`, `converted` count matches priced rows, stored values are `×5.40` — **F171-T10** (AC3 default path).
37. `POST /collection/import?currency=BRL` overrides detection; `?dry_run=true` → `dry_run: true`, no rows written, `canonize_scheduled: false`; `?currency=EUR` → `422`; existing `test_collection_import_canonize.py` still passes — **F171-T10** (AC3, AC8).
38. `dry_run` on the Liga no-price fixture via the API → `priced 0`, `currency_source "origin"` — **F171-T10**.
39. `import-csv --dry-run --file generic_usd_symbol.csv` prints `Currency: USD` (and `Source:`, `Confidence:`, `Priced rows:`); `--currency BRL` honored in the dry run; `--currency usd` (lower case) accepted — **F171-T13** (AC3, AC8).
40. `import-csv --currency EUR` → click usage error, exit code 2; answering `n` at the confirm prompt → `Aborted`, no writes; the real import stores converted values with a seeded/patched rate; the Liga no-price fixture → `Priced rows: 0`, `Source: origin` — **F171-T13**.
41. `CsvImportModal`: selecting a file triggers exactly one dry-run call; the detected currency/source is shown; the low-confidence warning renders when `currency_source === "default"` or `currency_confidence === "low"`; changing the select to USD sends `currency=USD` on the real import call — **F171-T11** (AC3, AC4).
42. `CsvImportModal`: the success screen shows `priced`/`converted` counts and (when `converted > 0`) the rate; `price_warnings` with 8 items renders only the first 5; `converted 0` hides the rate line; a dry-run failure still leaves the currency selector usable and import still possible; selecting a new file resets the previous detection — **F171-T11**. Both locale files (`pt-BR.json`, `en.json`) have identical key sets for the new keys.
43. `ImportPurchasesPage`: a mixed preview renders exactly one converted badge (`data-testid="purchase-converted-badge"`) for the USD row and none for the BRL row or for a row missing the new fields (legacy-response safety) — **F171-T12** (AC6).
44. `ImportPurchasesPage`: an unmatched row with `reason === "currency_conversion_failed"` shows that reason; `exchange_rate: null` with a USD row shows the badge without a rate tooltip — **F171-T12**.

## 6. Anotações para tasks

- (F171-T01, `liga_brl_no_price.csv`, `liga_brl_with_price.csv`, `generic_brl_symbol.csv`, `generic_usd_symbol.csv`, `manabox_usd.csv`, `manabox_brl.csv`, `ambiguous_no_hint.csv`, `purchase_usd_sample.html`)
- (F171-T02, none — pure functions, no shared fixture file needed)
- (F171-T03, `_fake_rate_lookup`)
- (F171-T04, `liga_brl_no_price.csv`, `liga_brl_with_price.csv`, `generic_brl_symbol.csv`, `generic_usd_symbol.csv`, `manabox_usd.csv`, `manabox_brl.csv`, `ambiguous_no_hint.csv`)
- (F171-T05, `purchase_usd_sample.html`)
- (F171-T06, none — pure function, no shared fixture file needed)
- (F171-T07, `liga_brl_no_price.csv`, `liga_brl_with_price.csv`, `generic_brl_symbol.csv`, `generic_usd_symbol.csv`, `manabox_usd.csv`, `manabox_brl.csv`, `ambiguous_no_hint.csv`, `_fake_rate_lookup`)
- (F171-T08, `purchase_usd_sample.html`, `_fake_rate_lookup`)
- (F171-T09, `_fake_rate_lookup`, `_stub_currency_converter_dep`)
- (F171-T10, `generic_usd_symbol.csv`, `liga_brl_no_price.csv`, `ambiguous_no_hint.csv`, `_stub_currency_converter_dep`)
- (F171-T11, `mockImportCollectionCsv`)
- (F171-T12, `mockPurchasePreviewWithConversion`)
- (F171-T13, `generic_usd_symbol.csv`, `liga_brl_no_price.csv`, `_fake_rate_lookup`)

T14 is a docs task with no `## Test scenarios` code obligation of its own; it is not annotated.

## Riscos para QA

- **AC5/AC7's "no rate → succeed, never store USD as BRL" invariant is the single most
  safety-critical behavior in this feature.** It is exercised in 4 different places (T03 unit,
  T07 CSV import, T08 purchases preview, T09 batch add) with 4 different fake-rate mechanisms
  (lambda, `Mock`, dependency override, patched method). QA should specifically grep all 4 test
  files for a `None`-rate case before sign-off, not just trust the AC checkbox — a gap in any one
  of the 4 call sites would silently reintroduce the original bug in a different code path.
- **The number-format ambiguity rules in `money.py` (T02) are the trickiest part of the spec** —
  `1.234` and `1,234` resolve differently depending on `hint`, and the brief's own worked examples
  (`1.234` with hint USD/None → `1.23` after 0.01 quantize) are non-obvious. QA should re-derive at
  least 3 of the ambiguous cases from the brief by hand and compare against the actual test
  assertions, the way the F16 retrospective flagged verifying edge cases against implementation
  rather than assumptions.
- **T09's file overlap with T10 in `routers/collection.py` / `schemas/collection.py` is sequenced,
  not isolated** (T09 in Wave 3, T10 in Wave 4, per the readiness report's Check 3). QA should diff
  both tasks' changes to those two files together at the end, since a Wave 4 edit could silently
  undo or shadow a Wave 3 one despite each task's own tests passing in isolation.
- **CLI test (T13) is the only place a real end-to-end write path is exercised outside the API** —
  it is also the only task touching the batch-wide high-conflict `src/cli/main.py`. QA should run
  `pytest tests/cli/test_import_csv_currency.py -v` in isolation after the full batch F171–F179
  lands, in case a sibling feature's edit to a different CLI command shifted line numbers enough to
  break the `import-csv` block's local imports.
- **Frontend tests (T11, T12) mock the API entirely and never run against the real T10 backend.**
  Per the plan, T10 ships in Wave 4 while T11 ships in Wave 1 against the documented contract only.
  QA should do one manual click-through of the CSV import modal (BRL file, USD file, ambiguous file)
  against a live local backend before promoting to `main`, since a contract drift between the shard
  and the actual `ImportResult` JSON would not be caught by either side's automated tests.

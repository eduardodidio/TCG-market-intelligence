# 05 — CsvImportModal currency UX (T11)

Files: `frontend/src/components/CsvImportModal.tsx`, `frontend/src/api/collection.ts` (`importCollectionCsv` ~L283),
`frontend/src/types/api.ts` (`ImportResult` ~L566), `frontend/src/i18n/locales/{pt-BR,en}.json`,
new test `frontend/src/components/__tests__/CsvImportModal.test.tsx`.

Flow:
1. User selects a file. The modal calls `importCollectionCsv(file, { dryRun: true })` and enters state `detecting`.
2. It shows "Detected currency: R$ (BRL) — source: <source>" plus `priced`/`total_csv_rows`.
   If `currency_source === "default"` or `currency_confidence === "low"`, it shows a yellow warning
   (`collection.importCurrencyLowConfidence`).
3. A `<select data-testid="csv-currency-select">` offers Auto (detected) / BRL / USD. The default is `auto`.
4. Import → `importCollectionCsv(file, { currency })`. The success screen adds priced/converted counts,
   the rate (when converted > 0), and up to 5 `price_warnings`.
5. If the dry run fails, the modal falls back to the old behavior (import still allowed, with the selector).

`ImportResult` TS additions (all optional): `detected_currency`, `currency_source`, `currency_confidence`,
`currency_evidence`, `priced`, `converted`, `exchange_rate`, `price_warnings`, `dry_run`.

i18n keys (T11 is the **sole owner** of both locale files for F171; it adds T12's key too):
`collection.importCurrencyLabel`, `collection.importCurrencyAuto`, `collection.importCurrencyDetected`,
`collection.importCurrencySource.{user,column,header,symbol,number_format,origin,default}`,
`collection.importCurrencyLowConfidence`, `collection.importPriced`, `collection.importConverted`,
`collection.importRate`, `collection.importPriceWarnings`, `purchases.convertedFrom`.
pt-BR copy follows the existing no-accent style of the file (e.g. "Moeda do arquivo").

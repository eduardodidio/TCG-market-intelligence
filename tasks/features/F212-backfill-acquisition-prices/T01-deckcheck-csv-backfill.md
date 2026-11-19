# T01 — CLI: Backfill Acquisition Prices from DeckCheck CSV

**Status:** planned
**Wave:** 0
**Estimate:** M

## User Story

As the collection owner, I want to bulk-import purchase prices from my
DeckCheck Binder CSV export so that my portfolio tracks what I actually paid.

## Problem

The existing `import-csv` command REPLACES the entire collection. We need a
command that only UPDATES `acquisition_price` on existing entries without
touching the collection itself.

## Dev Notes

### DeckCheck CSV Format
```
Card Scryfall ID,Name,Set Code,Collector Number,...,Purchase Price,...
a0e47d11-...,Abrade,vow,139,...,0.19,...
```
- Match by: `(Name, Set Code, Collector Number)` case-insensitive
- Price column: `Purchase Price` (USD, decimal dot)
- Quantity column: `Quantity` (use to verify match)

### New CLI Command: `backfill-prices`

```python
@cli.command("backfill-prices")
@click.option("--file", "csv_file", required=True, help="DeckCheck CSV path")
@click.option("--user-id", default="1", help="User ID")
@click.option("--currency", default="USD", help="Source currency")
@click.option("--dry-run", is_flag=True, help="Preview without applying")
@click.option("--overwrite", is_flag=True, help="Overwrite existing prices")
```

### Algorithm
1. Read CSV with `csv.DictReader`
2. Load all `user_collection` entries for the user
3. Build lookup dict: `(name_en.lower(), set_code.lower(), collector_number)` -> entry
4. For each CSV row:
   a. Match to collection entry by (Name, Set Code, Collector Number)
   b. Skip if entry already has `acquisition_price` (unless `--overwrite`)
   c. Convert USD price to BRL using `CurrencyConverter` (or a fixed rate if no DB rate)
   d. Update `acquisition_price` and optionally `acquired_at` from CSV `Created At`
5. Use `repo.update_collection_entry()` in a transaction
6. Print summary: matched/skipped/not_found/total

### Currency Conversion
- Use `src/services/currency.py` CurrencyConverter
- Fallback: if no exchange rate in DB, use a hardcoded recent rate (ask user)
- The DeckCheck CSV date is 2026-10-28, so look up USD/BRL rate for that date

### Edge Cases
- Card name might differ slightly (PT vs EN) -> match on `name_en` first
- Set code case: CSV has lowercase, DB may have mixed -> normalize both
- Collector number: exact match (string)
- Foil/non-foil: CSV has `Finish` column, collection has `is_foil` -> match on both if ambiguous

### Files to Create/Modify
- `src/cli/main.py` — add `backfill-prices` command
- `src/collection/price_backfill.py` — new module with backfill logic (testable)

### Existing Infrastructure to Reuse
- `src/collection/csv_columns.py` — column resolution (already maps `Purchase Price`)
- `src/currency/import_conversion.py` — `to_brl()` conversion
- `src/database/repository.py` — `update_collection_entry()`, `list_collection()`

## Testing

- Unit test: `tests/collection/test_price_backfill.py`
  - Test matching logic (exact, case-insensitive)
  - Test skip-if-already-set
  - Test overwrite mode
  - Test USD->BRL conversion
  - Test dry-run mode
- Integration: run with `--dry-run` on the actual CSV, verify match count ~915

```bash
python -m src.cli.main backfill-prices --file docs/deckcheck-binder-colecao-mtg-20261028.csv --dry-run
```

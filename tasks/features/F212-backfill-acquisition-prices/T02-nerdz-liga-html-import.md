# T02 — Run Nerdz+Liga HTML Import via Existing Pipeline

**Status:** planned
**Wave:** 0
**Estimate:** S

## User Story

As the collection owner, I want to import purchase prices from my Nerdz Cards
and Liga Magic order history HTMLs so I have acquisition costs for cards not
covered by the DeckCheck CSV.

## Problem

25 HTML purchase files exist in `docs/comprasEmLojas/` but have never been
imported. The infrastructure already exists (F135 ImportPurchasesPage).

## Dev Notes

### This is an EXECUTION task, not a code task

The pipeline already works:
1. `src/services/purchase_parser.py` — parses Nerdz Cards + Liga HTML
2. `src/services/purchase_matcher.py` — matches to collection entries
3. `src/api/routers/purchases.py` — `POST /purchases/import-preview` + `POST /purchases/apply`
4. Frontend: `ImportPurchasesPage` (drag-drop)

### Execution Plan

**Option A: Via API (scripted)**
Write a small script that:
1. Reads all HTML files from `docs/comprasEmLojas/`
2. Calls the parser directly
3. Runs the matcher
4. Applies prices via `repo.update_collection_entry()`

```python
# scripts/import_purchase_htmls.py
import glob
from src.services.purchase_parser import parse_purchase_html
from src.services.purchase_matcher import match_purchases
# ... load collection, match, apply
```

**Option B: Via Frontend (manual)**
1. Start the app: `python -m src.cli.main serve`
2. Open ImportPurchasesPage in browser
3. Drag-drop all 25 HTML files
4. Review matches, apply

### Preference: Option A (scripted)
Automated is better for 25 files. Create a one-off script that:
1. Parses all HTMLs
2. Matches to collection
3. Shows preview (match count, unmatched, confidence)
4. Applies with `--yes` flag or prompts for confirmation
5. Skips entries that already have `acquisition_price` (from T01)

### Files to Create
- `scripts/import_purchase_htmls.py` — one-off script

### HTML Files (25 total)
- 24 Nerdz Cards orders (BRL)
- 1 Liga Magic order (BRL)

## Testing

- Run script with dry-run first
- Verify matched count and prices
- Check no duplicates or overwrites

```bash
python scripts/import_purchase_htmls.py --dry-run
python scripts/import_purchase_htmls.py --apply
```

# 01 — Operational Pipeline

## Normalize Set Codes (T01)

Script: `scripts/normalize_set_codes.py`
- Safety: checks for duplicate conflicts before updating
- Updates `cards.set_code` and `source_cards.set_code` to LOWER()
- Default DB path: `tcg_market.db`

## Match Report (T02)

CLI: `python -m src.cli.main match-report --output reports/match-report.json`
- Read-only operation — no DB writes
- Searches MYP for each collection card
- Reports: matched (sku/name+set/name-only), ambiguous, unmatched
- Uses asyncio.Semaphore(3) concurrency, 1s delay

## Sync Collection (T06)

CLI: `python -m src.cli.main sync-collection`
- Full pipeline: search -> match -> fetch details -> upsert card -> fetch history -> store observations -> link collection entry
- Rate-limited: ~35-40 min for 548 cards
- skip_matched=True by default (skips already-linked entries)
- 365 days of history

## Verify Dashboard (T07)

- Start API: `python -m src.cli.main serve`
- Open frontend: `http://localhost:5173`
- Check: collection value, linked count, set coverage, Scryfall images

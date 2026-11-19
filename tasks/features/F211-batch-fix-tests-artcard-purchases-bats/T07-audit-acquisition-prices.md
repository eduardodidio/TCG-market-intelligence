# T07 — Audit Acquisition Prices in Collection

**Status:** planned
**Wave:** 0
**Estimate:** S

## User Story

As the collection owner, I want to know how many cards have acquisition
prices set, how many are missing, and whether a re-import is needed.

## Problem

User previously provided purchase price data. Need to verify if that data
was successfully applied to the collection and assess current state.

## Dev Notes

### Approach (research/query task, no code changes)

1. Query the Neon database for acquisition price stats:
   ```sql
   SELECT
     COUNT(*) AS total_cards,
     COUNT(acquisition_price) AS with_price,
     COUNT(*) - COUNT(acquisition_price) AS without_price,
     SUM(acquisition_price * quantity) AS total_invested
   FROM user_collection
   WHERE user_id = (SELECT id FROM users LIMIT 1);
   ```

2. List the top cards without acquisition prices:
   ```sql
   SELECT name_en, set_code, collector_number, quantity
   FROM user_collection
   WHERE user_id = (SELECT id FROM users LIMIT 1)
     AND acquisition_price IS NULL
   ORDER BY name_en
   LIMIT 20;
   ```

3. Check if previous purchase HTML files exist in `docs/` or if there
   are import logs.

4. Report findings to user with:
   - Total cards with/without prices
   - Total investment value
   - Recommendation: re-import needed? Which files?

### Existing Infrastructure
- `POST /purchases/import-preview` — preview matched purchases
- `POST /purchases/apply` — apply acquisition prices
- `ImportPurchasesPage` — drag-drop HTML frontend
- `src/services/purchase_parser.py` — Nerdz Cards HTML parser
- `src/services/purchase_matcher.py` — cascading card name matching

### Files: None (query-only task)

## Testing

- No code changes, no tests needed
- Output: acquisition price report for user review

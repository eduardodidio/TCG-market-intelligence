# T03 — Verify & Report Final Acquisition Price Coverage

**Status:** planned
**Wave:** 1
**Estimate:** S
**Depends on:** T01, T02

## User Story

As the collection owner, I want a final report showing how many cards now
have acquisition prices, the total invested value, and which cards remain
uncovered.

## Dev Notes

### This is a QUERY task — no code changes

After T01 (DeckCheck CSV) and T02 (Nerdz+Liga HTML) complete, run:

```sql
-- Summary
SELECT
  COUNT(*) AS total,
  COUNT(acquisition_price) AS with_price,
  COUNT(*) - COUNT(acquisition_price) AS without_price,
  ROUND(SUM(CASE WHEN acquisition_price IS NOT NULL
    THEN acquisition_price * quantity ELSE 0 END), 2) AS total_invested_brl
FROM user_collection
WHERE user_id = (SELECT id FROM users LIMIT 1);

-- Cards still missing prices
SELECT name_en, set_code, collector_number, quantity
FROM user_collection
WHERE user_id = (SELECT id FROM users LIMIT 1)
  AND acquisition_price IS NULL
ORDER BY name_en;

-- Coverage by set
SELECT set_code,
  COUNT(*) AS total,
  COUNT(acquisition_price) AS with_price,
  ROUND(100.0 * COUNT(acquisition_price) / COUNT(*), 1) AS pct
FROM user_collection
WHERE user_id = (SELECT id FROM users LIMIT 1)
GROUP BY set_code
ORDER BY pct ASC;
```

### Expected Outcome
- Target: 900+ entries with prices (from 0 → ~77-90% coverage)
- Total invested: ~R$ 15,000-20,000 (USD $2,540 converted + BRL from Nerdz)
- Remaining gaps: cards not in DeckCheck nor in any purchase order

## Testing

- No code changes, no automated tests
- Output: coverage report for user review

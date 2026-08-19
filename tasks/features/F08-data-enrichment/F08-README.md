# F08 -- Data Enrichment

**Status:** done
**Created:** 2026-08-19
**Gandalf Decision:** D-20260819-001

## Summary

Fix three data quality issues found during manual testing of the F07 dashboard:
double-encoded UTF-8 card names, flat movers due to wrong default period, and
insufficient data variety (only 30 cards from 1 set). This is a single unified
feature covering encoding fix, movers tuning, and collection expansion.

## Waves

| Wave | Tasks       | Description |
|------|-------------|-------------|
| 0    | T01, T02    | Fix UTF-8 encoding in parser/provider + migrate existing DB data. Change movers default from 7d to 30d on Dashboard. |
| 1    | T03         | Collection expansion -- backfill popular sets using existing infrastructure. |
| 2    | T04         | End-to-end validation, documentation, diagrams, README update. |

## Risk Assessment

- **Encoding fix (T01)** is the riskiest task. Root cause must be diagnosed
  precisely: is `curl_cffi`'s `resp.text` using the wrong charset, or is the
  HTML declaring an incorrect charset? The fix must handle both new fetches
  and existing corrupted DB data.
- **Movers tuning (T02)** is trivial -- a single constant change in the
  frontend.
- **Collection expansion (T03)** is operational -- the backfill infrastructure
  already supports multi-set collection with resume, concurrency, and retry.
  The main risk is runtime (many cards to fetch with rate limiting).
- **Validation (T04)** is straightforward verification and documentation work.

## Dependencies

- F06 REST API must be functional (it is -- shipped)
- F07 Frontend must be functional (it is -- shipped)
- Backfill infrastructure from F01/F04 must work (it does)

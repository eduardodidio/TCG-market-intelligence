# F01 — MYP Cards Backfill (Dominaria Remastered)

**Status:** completed
**Created:** 2026-08-18
**Owner:** Eduardo Rutkoski Didio

## Objective

Run the full backfill of Dominaria Remastered set from MYP Cards, validate
data quality, fix any issues found, and confirm the collector is production-ready
for scaling to all sets.

## Tasks

| Task | Description | Status |
|------|-------------|--------|
| F01-T01 | Run full backfill of DMR set | done |
| F01-T02 | Validate data quality in DB | done |
| F01-T03 | Fix any issues found | done |
| F01-T04 | Run tests and confirm green | done |

## Waves

- **Wave 0:** F01-T01 (backfill execution)
- **Wave 1:** F01-T02, F01-T03 (validation + fixes)
- **Wave 2:** F01-T04 (final test run)

## Success Criteria

1. All 30 cards of DMR set collected with zero failures
2. Price observations > 0 for each card that has history
3. Idempotency verified (re-run inserts 0 new observations)
4. All unit tests passing
5. No encoding issues in stored data

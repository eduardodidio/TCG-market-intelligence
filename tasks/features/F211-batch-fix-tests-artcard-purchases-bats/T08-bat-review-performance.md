# T08 — Review BAT Files + Run Push-All Performance Test

**Status:** planned
**Wave:** 0
**Estimate:** M

## User Story

As the system operator, I want to verify my BAT files are correct and
measure the performance of the price sweep to ensure it runs efficiently.

## Problem

9 BAT files in `bats/` need review for correctness after recent changes
(Liga removal, MYP-only sweep). Then run the main price sweep to measure
real-world performance.

## Dev Notes

### Part 1: BAT Review Checklist

Review each BAT for:
- Correct CLI command names (no stale references to liga-sweep)
- Proper error handling
- Correct working directory resolution
- Appropriate timeouts/limits
- esteira_bats.bat sequencing correctness

**BATs to review:**
1. `push-all.bat` — `myp-sweep --max-age-days 1`
2. `daily-scan.bat` — myp-sweep + process-queue + snapshot
3. `process-queue.bat` — `process-price-requests --limit 100`
4. `esteira_bats.bat` — orchestrates all 7 bats
5. `banlist-sync.bat` — `banlist-sync`
6. `collect-metagame.bat` — `collect-metagame --limit 20`
7. `daily-snapshot.bat` — `daily-snapshot`
8. `deck-suggestions.bat` — `process-deck-suggestions --limit 10`
9. `fetch-news.bat` — `fetch-news --max-per-source 30`
10. `catalog-seed-fra.bat` — one-off FRA seed

### Part 2: Performance Test

Run the push-all equivalent:
```bash
time python -m src.cli.main myp-sweep --max-age-days 1
```

Measure and report:
- Total execution time
- Number of cards processed
- Success/failure/skip counts
- Rate (cards/minute)
- Any errors or rate-limiting issues

### Files: None modified (review + run only)

## Testing

- No code changes, no automated tests
- Output: BAT review notes + performance report

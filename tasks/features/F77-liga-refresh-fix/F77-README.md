# F77 — Liga Refresh Fix

**Status:** planned
**Wave:** 0 (parallel with F78, F79, F81)

## Summary
Fix POST /collection/{id}/refresh-liga returning "No price found on LigaMagic for this card" when the Liga page actually has price data. Root cause: the parser or browser fetch silently fails and returns empty prices.

## Tasks
| Task | Description | Wave |
|------|-------------|------|
| F77-T01 | Debug Liga HTML + fix parser/fetch | 0 |
| F77-T02 | Add diagnostic logging to Liga refresh flow | 0 |
| F77-T03 | Tests for parser with real Liga HTML samples | 0 |

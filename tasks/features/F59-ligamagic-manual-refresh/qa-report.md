# F59 QA Report

**Verdict:** PASS

## Test Results
- Backend: 472 passed / 1 failed (pre-existing, unrelated to F59)
- Frontend: 976 passed / 0 failed
- F59-specific backend: 16 passed / 0 failed
- F59-specific frontend: 21 passed / 0 failed

## Pre-existing Failure (Not F59)

`tests/cli/test_seed_users.py::TestSeedUsers::test_creates_both_users_with_env_password` -- this test expects `anderson.serafim` user to be created, but commit `9d6d74c` ("remove anderson.serafim from seed") removed that user. The test was not updated to match. This predates F59 and is tracked as a known issue.

## Acceptance Criteria

- [x] AC1: Card detail page shows a "LigaMagic" refresh button -- violet `bg-violet-600` button with globe SVG, rendered at `CollectionCardDetail.tsx:328-331` with `data-testid="refresh-liga-btn"`
- [x] AC2: Button triggers backend call -- `handleRefreshLiga` calls `refreshCardPriceLiga(entryId, ...)` which hits `POST /collection/{entry_id}/refresh-liga`
- [x] AC3: Loading state with spinner -- `refreshingLiga` state disables button, `animate-spin` on globe SVG, `disabled:opacity-50 disabled:cursor-not-allowed`
- [x] AC4: Success: price updates, source badge "liga" -- `PriceSourceBadge` renders violet badge with "LigaMagic" text for `source="liga"`, success toast auto-dismisses after 5s
- [x] AC5: Failure: error message, no crash -- endpoint catches `LigaNotFoundError`, `LigaRateLimitError`, `LigaError`, and bare `Exception`; all return 200 with warnings (no 500s)
- [x] AC6: PriceSourceBadge renders "LigaMagic" for source="liga" -- confirmed at `PriceSourceBadge.tsx:16`, violet badge with globe icon, i18n key `priceSource.liga`
- [x] AC7: Timeout is generous -- `refreshCardPriceLiga` uses `timeoutMs: 45000` (45s), exceeding the 30s spec
- [x] AC8: Button only visible when card has a name -- conditional render `{!!(entry.name_en || entry.name_pt) && (` at line 328, plus early return guard in handler at line 89-90

## Security

- Auth enforced via `require_auth_or_api_key` dependency
- IDOR protection: `entry.user_id != user_id` check returns 404
- Provider cleanup: `await provider.close()` in `finally` block ensures Playwright browser is always closed

## i18n

All 7 keys present in both `en.json` and `pt-BR.json`:
- `collection.refreshLiga`, `collection.refreshLigaTooltip`, `collection.refreshLigaSuccess`
- `collection.refreshLigaNotFound`, `collection.refreshLigaError`, `collection.refreshLigaRateLimit`
- `priceSource.liga`

## Regressions

None found. The single backend failure is pre-existing (seed_users test not updated after commit 9d6d74c).

## Recommendations

1. **Fix pre-existing seed_users test** -- `test_creates_both_users_with_env_password` needs updating to remove the `anderson.serafim` assertion. This is unrelated to F59 but should be addressed.

2. **Unused i18n keys (low priority)** -- As the TechLead noted, `collection.refreshLigaNotFound` and `collection.refreshLigaRateLimit` are defined but the frontend handler shows the raw backend message instead of mapping to these keys. Either remove the keys or add frontend-side message mapping for full localization support.

# F132 -- Price Request Queue Fix

**Status:** planned
**Branch:** homol
**Wave count:** 1 (Wave 0 -- all tasks parallel)

## Problem

The price request queue system (shipped in F130) has several issues that
prevent it from working end-to-end:

1. **Timeout bug**: Users clicking "refresh price" on a CardTile see a timeout
   error. The `POST /cards/{card_id}/refresh-price` endpoint only inserts a
   DB row (should be <100ms), but the frontend `apiPost` uses
   `DEFAULT_TIMEOUT_MS = 10_000` with no custom override. On Render/Neon cold
   start this may be too tight. The real issue is likely that the `refreshCardPrice`
   function in `frontend/src/api/cards.ts` does not pass a custom `timeoutMs`,
   while the similar `searchCardsWeb` already passes `35_000`.

2. **No frontend polling**: After queuing, CardTile shows a clock icon for 5
   seconds (`setTimeout`) then clears it. It never calls the existing
   `GET /cards/{card_id}/price-request-status` endpoint, so the user never
   sees the result.

3. **Automation gap**: `daily-scan.bat` already includes `process-price-requests`
   (verified in current codebase), but task T02 should confirm the ordering
   is correct and add a `--limit` flag if missing.

4. **No admin trigger**: The admin panel shows the price request queue
   (AdminPriceRequestsSection) but has no button to trigger processing. Since
   Liga requires Playwright from a residential IP, the admin trigger must
   record the intent (or run on the local machine). The new endpoint should
   follow the pattern of `POST /admin/jobs/liga-scan`.

## Goal

Make the price request queue fully operational: fix the timeout, add real
polling so users see when their request completes, ensure automation runs
daily, and give admins a manual trigger button.

## Tasks (Wave 0 -- all parallel)

| Task | File | Summary |
|------|------|---------|
| T01 | `F132-T01-debug-timeout.md` | Debug and fix the timeout on refresh-price |
| T02 | `F132-T02-daily-scan-automation.md` | Verify/fix process-price-requests in daily-scan.bat |
| T03 | `F132-T03-frontend-polling.md` | Poll price-request-status, spinner, update on completion |
| T04 | `F132-T04-admin-trigger.md` | Admin endpoint + UI button to trigger queue processing |

## Key Files

- `src/database/models.py` (lines 601-630) -- PriceUpdateRequestRow model
- `src/api/routers/cards.py` (lines 260-326) -- refresh-price + status endpoints
- `src/cli/main.py` (lines 1181-1294) -- process-price-requests CLI
- `frontend/src/api/client.ts` -- DEFAULT_TIMEOUT_MS, apiPost
- `frontend/src/api/cards.ts` -- refreshCardPrice, fetchPriceRequestStatus (new)
- `frontend/src/components/CardTile.tsx` (lines 51-68) -- handleRefresh
- `daily-scan.bat` -- daily automation script
- `src/database/repository.py` (lines 4632-4765) -- price request repo methods
- `src/api/routers/admin.py` -- admin router (jobs section)
- `frontend/src/components/admin/AdminPriceRequestsSection.tsx` -- admin UI

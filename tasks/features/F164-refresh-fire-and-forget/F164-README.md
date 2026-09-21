# F164 — Card Refresh Fire-and-Forget UX

**Status:** completed
**Wave:** 0 (parallel with F165, F166, F167)
**Tasks:** 2
**Files touched:** `frontend/src/components/CardTile.tsx`, `frontend/src/hooks/usePriceRequestPolling.ts`, tests

## Summary

When clicking the refresh button on a CardTile, the button stays disabled with a spinner while polling for price completion. The user wants "fire and forget" — enqueue the request, show brief confirmation, and immediately release the button. The cron (`bats/process-queue.bat`) handles actual processing.

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| F164-T01 | Remove polling from CardTile, fire-and-forget UX | 0 |
| F164-T02 | Tests for fire-and-forget behavior | 0 |

## Architecture Notes

- Keep `usePriceRequestPolling` in codebase — it's still used by CardDetail page
- CardTile: after `status: "queued"`, show "Enfileirado" badge for 1.5s, then reset button to idle
- Remove `queued` state from disabling the button — only `refreshing` (the API call itself) should disable
- CardDetail page can keep polling for real-time updates if desired

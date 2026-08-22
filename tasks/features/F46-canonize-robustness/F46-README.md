# F46 Canonize Robustness

**Status: planned**

## Problem

The canonize endpoint creates a canonical card and links it to the collection
entry (steps 1-2), then attempts to fetch MYP data (step 3). Step 3 has a
`try/finally` but no `except` -- if `get_card_details()` raises (e.g. MYP
404), the exception propagates as HTTP 500 even though the card IS already
linked. The frontend catch block shows an error toast but never re-fetches the
entry, so button state gets stuck showing "Vincular" instead of "Refresh".

## Root Causes

1. **Backend**: `collection.py` line 529 uses `try/finally` without `except`.
   Any exception inside the MYP fetch block (lines 530-570) bubbles up as a
   500 despite steps 1-2 having committed successfully.
2. **Frontend**: `CollectionCardDetail.tsx` `handleCanonize` (line 81) catches
   the 500 and shows an error message, but does NOT call `refetch()` to reload
   the entry. The UI remains in the "unlinked" state even though `card_id` is
   now set on the server.

## Scope

Two files, two tasks, one wave. No new dependencies.

## Wave Plan

### Wave 1 (parallel)

| Task | Title | Files |
|------|-------|-------|
| T01 | Backend: canonize endpoint error handling | `src/api/routers/collection.py`, tests |
| T02 | Frontend: re-fetch after canonize + button state | `frontend/src/pages/CollectionCardDetail.tsx`, tests |

## Acceptance Criteria (feature-level)

- Canonize succeeds (HTTP 200) even when MYP fetch fails; response includes a
  warning field when MYP data could not be fetched.
- After canonize with MYP failure, the card detail page shows the refresh
  button (not the canonize button).
- After canonize with MYP failure, the user sees a warning message (not a
  hard error).
- Existing happy-path canonize behavior is unchanged.

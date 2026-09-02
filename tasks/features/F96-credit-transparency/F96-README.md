# F96 — Credit Transparency & Recovery

**Status:** planned

## Problem

Users do not see the credit cost of actions until after clicking and opening
the confirmation modal. When credits are insufficient, the modal shows a red
message but offers no recovery path (no link to claim bonus, no guidance on
earning more). Scheduled scan failures due to insufficient credits go
unnoticed. Bonus claims have no visible feedback beyond the balance update.

## Goals

1. Show credit cost inline on action buttons **before** click (small badge).
2. Enhance insufficient-credits state in CreditConfirmModal: add "Claim
   Bonus" shortcut (when eligible) and "How to earn" guidance text.
3. Show a brief success message after bonus claim in TreasureBalance.
4. Enhance the admin scheduled scan table to surface the
   `paused_insufficient_credits` status more prominently.
5. i18n for all new strings (EN + PT-BR).

## Scope

Primarily frontend. No new backend endpoints. No new dependencies.

## Task List

| Task | Title | Wave | Depends |
|------|-------|------|---------|
| T01  | Enhance CreditConfirmModal (claim bonus + earn info) | 0 | - |
| T02  | Bonus claim success feedback in TreasureBalance | 0 | - |
| T03  | Inline cost badge on single refresh buttons | 1 | T01 |
| T04  | Inline cost badge on bulk refresh button | 1 | T01 |
| T05  | Admin scheduled scan credit-pause indicator | 2 | - |
| T06  | i18n: EN + PT-BR keys for all new strings | 0 | - |

## Waves

### Wave 0 (parallel: T01, T02, T06)
- T01: Add "Claim Bonus" button + "earn info" section to CreditConfirmModal
  when balance is insufficient.
- T02: Show a brief animated success message in TreasureBalance after
  claiming bonus (reuse existing `claimed` state pattern, add text).
- T06: Add all new i18n keys to both locale files upfront so T01-T05 can
  reference them immediately.

### Wave 1 (parallel: T03, T04 -- depends on Wave 0)
- T03: Add `(1 token)` cost badge to refresh-liga and refresh-myp buttons
  on CollectionCardDetail and CollectionCardTile.
- T04: Add estimated cost badge to "Refresh All" button on MyCollection,
  leveraging the existing scan preview data.

### Wave 2 (T05 -- independent but last for review convenience)
- T05: Enhance ScheduleTable StatusBadge for `paused_insufficient_credits`
  with a more prominent indicator (icon + tooltip explaining recovery).

## Test Impact

Existing test files that exercise affected components and will need updates:
- `frontend/tests/components/CreditConfirmModal.test.tsx`
- `frontend/tests/components/TreasureBalance.test.tsx`
- `frontend/tests/components/ScheduleTable.test.tsx`
- `frontend/tests/pages/CollectionCardDetail.test.tsx`
- `frontend/tests/pages/MyCollection.test.tsx`

## Estimated New i18n Keys: ~12 (EN + PT-BR)

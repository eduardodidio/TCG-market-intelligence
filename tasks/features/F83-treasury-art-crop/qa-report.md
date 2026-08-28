# F83 — Treasury Art Crop — QA Report

**Date:** 2026-08-28
**Verdict:** PASS

## Test Results

| Suite | Passed | Failed | Total |
|-------|--------|--------|-------|
| Backend (all) | 2487 | 0 | 2487 |
| Frontend (all) | 1211 | 0 | 1211 |

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| TreasureTokenCard shows only art portion (no card name bar, no type line from image) | PASS | Line 27 of TreasureTokenCard.tsx uses `h-36 object-cover object-center` which constrains height and crops overflow, centering on the art |
| Token count badge overlay still visible | PASS | Badge div (lines 30-37) uses `absolute bottom-1 right-1` positioning inside the relative art box container — unaffected by the image crop |
| CreditConfirmModal renders correctly with cropped art | PASS | CreditConfirmModal.tsx imports and renders TreasureTokenCard at line 55 — no changes to the modal itself |
| Both treasure.jpg (EN) and tesouro.png (PT-BR) crop correctly | PASS | Image source comes from `useTreasureImage()` hook; the `object-cover object-center` CSS applies identically regardless of source image |
| TreasureModal (full-screen on click) unchanged | PASS | TreasureModal.tsx has no `object-cover` or `object-contain` — shows full card image unmodified |
| TreasureBalance sidebar thumbnail unchanged | PASS | TreasureBalance.tsx already uses its own `object-cover` styling (line 45), not affected by this change |
| All existing treasure tests pass | PASS | TreasureTokenCard.test.tsx (7 tests), TreasureModal.test.tsx, TreasureBalance.test.tsx all pass |

## Change Summary

Single-line CSS change in `frontend/src/components/TreasureTokenCard.tsx` line 27:
- Before: `object-contain` (showed full card with letterboxing)
- After: `h-36 object-cover object-center` (crops to art-only, fixed height)

## Regressions

None detected. All 2487 backend and 1211 frontend tests pass with zero failures.

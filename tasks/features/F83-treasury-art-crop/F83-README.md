# F83 — Treasury Art Crop

**Status:** done
**Wave structure:** Wave 0 (parallel with F84)
**Dependencies:** None

## Summary

The TreasureTokenCard component in the CreditConfirmModal shows the full MTG card image including the "TREASURE" header bar and "Token Artifact — Treasure" footer bar from the original card art. The fix crops the image to show only the treasure art portion (no card frame header/footer) while keeping the token count badge overlay.

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| F83-T01 | Crop treasure image to art-only in TreasureTokenCard | 0 |

## Acceptance Criteria

- TreasureTokenCard shows only the art portion of the treasure image (no card name bar, no type line from the image itself)
- Token count badge overlay still visible
- CreditConfirmModal renders correctly with cropped art
- Both treasure.jpg (EN) and tesouro.png (PT-BR) crop correctly
- TreasureModal (full-screen on click) unchanged — still shows full card
- TreasureBalance sidebar thumbnail unchanged
- All existing treasure tests pass

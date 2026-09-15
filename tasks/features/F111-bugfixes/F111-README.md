# F111 — Bugfixes Batch

**Status:** planned

## Scope
Three known bugs to fix in a single batch.

## Wave Plan

### Wave 0 (all parallel — independent fixes)

| Task | Bug | Fix |
|------|-----|-----|
| T01 | `catalog stats` "cards with price" shows 0 | Fix external_id mismatch: use card_id JOIN instead of external_id IN subquery |
| T02 | push-db stale frontend cache | After `/db/restore`, broadcast cache invalidation; frontend detects and forces re-auth |
| T03 | Collection disappeared (My Collection empty) | Investigate and fix — likely related to push-db or DB restore losing user_collection data |

## Dependencies
- None — all fixes are independent

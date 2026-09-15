# T1 — Enhance Share Collection Endpoint

**Wave:** 0
**Type:** Backend
**Estimate:** Small

## User Story

As a user browsing the marketplace, I want to see metadata about a shared
collection (total cards, sets represented, when it was shared) so I can
decide whether to browse it.

## Current Behavior

`GET /marketplace/listings/{share_code}` returns:
```json
{
  "share_code": "abc123",
  "listings": [...],
  "count": 5
}
```

No metadata about the collection itself (total count, sets, shared_at).

## Desired Behavior

Enhance the response to include a `collection_info` object:
```json
{
  "share_code": "abc123",
  "collection_info": {
    "total_cards": 142,
    "sets": ["mh3", "fdn", "cmm"],
    "shared_at": "2026-09-01T12:00:00"
  },
  "listings": [...],
  "count": 5
}
```

## Dev Notes

### Files to modify:
- `src/api/routers/marketplace.py` — `get_shared_collection()` endpoint at
  line 69. After fetching the `SharedCollectionRow`, query additional metadata.
- `src/database/repository.py` — Add a `get_shared_collection_stats(user_id)`
  method that returns total card count and distinct set codes from
  `user_collection` joined to `cards`.

### Implementation details:
- The `SharedCollectionRow` already has `shared_at` and `user_id`.
- Query `user_collection` WHERE `user_id = shared.user_id` to get counts.
- Do NOT expose user_id or email in the response (anonymized).
- The endpoint already uses `get_optional_user` — keep it public (no auth
  required for viewing).

### Edge cases:
- Share code not found -> 404 (already handled).
- Shared collection with 0 cards -> return empty `sets: []`, `total_cards: 0`.

## Testing

### Unit tests (pytest):
- `test_shared_collection_stats_returns_counts` — mock repo, verify response shape.
- `test_shared_collection_stats_empty_collection` — 0 cards case.
- `test_shared_collection_not_found_404` — invalid share code.

### Integration test:
- Create user, toggle sharing, add cards, call endpoint, verify `collection_info`.

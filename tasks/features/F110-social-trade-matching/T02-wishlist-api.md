# T02 -- Wishlist CRUD API Endpoints

**Wave:** 1 (Backend)
**Depends on:** T01
**Blocks:** T05

## User Story

As a user, I want to add cards to my wishlist, view my wishlist, remove
items, and mark cards as acquired so I can track what I still need.

## Dev Notes

### New router: `src/api/routers/wishlist.py`

Prefix: `/api/v1/wishlist`, tags: `["wishlist"]`

| Method | Path                | Description                        | Auth |
|--------|---------------------|------------------------------------|------|
| GET    | `/`                 | List wishlist (paginated, filtered) | yes  |
| POST   | `/`                 | Add card to wishlist                | yes  |
| DELETE | `/{card_id}`        | Remove card from wishlist           | yes  |
| PATCH  | `/{card_id}/acquire`| Mark as acquired                   | yes  |
| GET    | `/check`            | Check if card_ids are in wishlist   | yes  |

### Schemas: `src/api/schemas/wishlist.py`

```python
class WishlistAddRequest(BaseModel):
    card_id: int
    notes: str | None = None
    max_price: float | None = None

class WishlistItem(BaseModel):
    id: int
    card_id: int
    name_en: str
    name_pt: str | None
    set_code: str | None
    collector_number: str | None
    notes: str | None
    max_price: float | None
    is_acquired: bool
    acquired_at: str | None
    created_at: str
    # Enrichment (joined from cards / price_observations)
    image_uri: str | None = None
    current_price: float | None = None

class WishlistCheckResponse(BaseModel):
    wishlisted: list[int]  # card_ids that are in wishlist
```

### Implementation details

- On POST, look up CardRow by card_id to populate denormalized fields
  (name_en, name_pt, set_code, collector_number). Return 404 if card not found.
- On GET, support query params: `search` (name filter), `acquired` (bool),
  `limit`, `offset`. Optionally enrich with current price from latest
  price observation.
- On DELETE, use user_id + card_id (not wishlist row id) for simplicity.
- `/check?card_ids=1,2,3` -- accepts comma-separated card_ids, returns which
  ones are in the user's wishlist. Used by frontend to show "wishlisted" state.

### Register router

Add to `src/api/app.py`: `app.include_router(wishlist.router, prefix="/api/v1")`

## Testing

- Test CRUD happy path (add, list, remove, acquire)
- Test 404 when adding nonexistent card_id
- Test duplicate add returns 409 or is idempotent
- Test auth required (401 without token)
- Test `/check` endpoint with mix of wishlisted and non-wishlisted ids
- Test pagination and search filter

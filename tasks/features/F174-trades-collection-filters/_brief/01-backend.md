# F174 — Component: Backend queries & endpoints

## Current state (read before coding)
- `src/api/routers/marketplace.py`
  - `GET /marketplace/listings` → `browse_listings(limit, offset, set_code, search)`
    → `MarketplaceService.get_listings` (`src/marketplace/service.py:43`)
    → `Repository.list_marketplace_entries` (`src/database/repository.py:4167`).
    Order is hard-coded to `name_en ASC`. `latest_price` comes from
    `repo.get_latest_prices_batch(card_ids)` and `estimated_fee` from
    `src.marketplace.fees.calculate_trade_fee(price)`.
  - `GET /marketplace/listings/{share_code}` — **path param**. A new static
    route `/listings/sets` MUST be declared **above** it in the file, or
    FastAPI will match `sets` as a share_code.
  - `GET /marketplace/my-trades` — small (≤100) list with no filters. **Left unchanged**:
    filtering is client-side (see `03-trade-pages.md`).
- `src/api/routers/trade_match.py`
  - `GET /trade/duplicates` → `repo.get_user_duplicates(user_id, limit, offset)`
    (`repository.py:4847`). Order: `quantity DESC, name_en`. Returns an `ApiResponse`
    envelope via `success_response(result, total=total)`.
  - `GET /trade/duplicates/count` uses the same repo method. **Leave as is.**
- Join detail: `SharedCollectionRow.user_id` (int) is joined to
  `UserCollectionRow.user_id` (string) through
  `sa_cast(SharedCollectionRow.user_id, SAString)`. Copy this exactly.
- Price sort pattern (copy from `Repository.list_collection`, ~line 1823): a
  correlated scalar subquery on `PriceObservationRow` with
  `source == "liga"` and `external_id IN (liga_{card_id}, liga_{card_id}_foil)`,
  ordered by `observed_at DESC LIMIT 1`, with NULLs pushed last via
  `case((expr.is_(None), 1), else_=0)`. Per CLAUDE.md, a Liga sweep stores
  `external_id='liga_{card_id}'` (the `mid` price).
- Set names: `UserCollectionRow.set_name_en` (see
  `Repository.get_collection_sets`, line ~2020, which does `func.max(set_name_en)` grouped
  by `set_code`).

## Design — new module (conflict isolation)
`src/database/repository.py` is a 5k-line file that several batch features may
edit. **Do not modify it.** Instead, create **`src/marketplace/trade_queries.py`**:

```python
class TradeQueries:
    """Filtered/sorted read queries for the trades area (F174)."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo              # reuse repo.engine + repo.get_latest_prices_batch
        self.engine = repo.engine

    def list_listings(self, *, limit=20, offset=0, set_code=None, search=None,
                      exclude_user_id=None, share_code=None,
                      sort_by="name", sort_dir="asc") -> list[dict]: ...
    def list_listing_sets(self, *, exclude_user_id=None) -> list[dict]:
        # [{"set_code", "set_name", "count"}] ordered by set_code
    def list_duplicates(self, user_id, *, limit=50, offset=0, search=None,
                        set_code=None, sort_by="quantity", sort_dir="desc"
                        ) -> tuple[list[dict], int]: ...
    def list_duplicate_sets(self, user_id) -> list[dict]:
        # [{"set_code", "set_name", "count"}] of entries with quantity>1 & card_id not null
```

- `list_listings` returns **exactly** the same dict shape as
  `Repository.list_marketplace_entries` (same keys). Its default sort (`name asc`)
  gives the same order as today.
- `list_duplicates` returns the same dict shape as `Repository.get_user_duplicates`,
  with the same WHERE clause. Its default sort (`quantity desc`, then `name_en`) gives
  the same order as today.
- Sort whitelist — module constants:
  - `LISTING_SORTS = {"name": name_en, "set": set_code, "number": collector_number, "price": <liga subquery>}`
  - `DUPLICATE_SORTS = {"quantity": quantity, "name": name_en, "set": set_code, "number": collector_number, "price": <liga subquery>}`
  - An unknown `sort_by` raises `ValueError`. The router validates first, so this is defence in depth.
  - Always add `UserCollectionRow.id ASC` as the final tiebreaker so pagination is deterministic.
  - Nullable string columns: `func.coalesce(col, "")` for asc. NULL prices always sort last.
- Search: `ilike(f"%{search}%")` on `name_en | name_pt`. Strip it, and treat an
  empty string as None.
- `set_code` comparison: case-insensitive (`func.lower(col) == set_code.lower()`).
  The frontend sends lowercase codes from the facet endpoint.

## Endpoint changes
### `GET /api/v1/marketplace/listings` (extend)
New query params:
- `sort_by: str = Query("name", pattern="^(name|set|number|price)$")`
- `sort_dir: str = Query("asc", pattern="^(asc|desc)$")`

Pass them through `MarketplaceService.get_listings` (add kwargs with defaults), which calls
`TradeQueries(self.repo).list_listings(...)`. Response shape is unchanged:
`{"listings": [...], "count": n}`.

### `GET /api/v1/marketplace/listings/sets` (new, declared before `/listings/{share_code}`)
Optional auth (`get_optional_user`) excludes the viewer's own cards, like `/listings`.
Response: `{"sets": [{"set_code": "mh3", "set_name": "Modern Horizons 3", "count": 12}]}`.

### `GET /api/v1/trade/duplicates` (extend)
New params:
- `search: str | None = Query(None, max_length=100)`
- `set_code: str | None = Query(None, max_length=10)`
- `sort_by: str = Query("quantity", pattern="^(quantity|name|set|number|price)$")`
- `sort_dir: str = Query("desc", pattern="^(asc|desc)$")`

It uses `TradeQueries(repo).list_duplicates(...)`. The envelope and `total` are
unchanged, and `total` reflects the filters.

### `GET /api/v1/trade/duplicates/sets` (new)
Auth required. Response: `success_response([{"set_code", "set_name", "count"}])`.
Declare it before any path-param route (none exists today, but keep the
static routes grouped at the top).

## Validation / security
- `limit`/`offset` bounds are unchanged.
- The regex `pattern` on `sort_by`/`sort_dir` gives FastAPI a 422 on invalid values. Never
  interpolate user input into SQL. Sorting is resolved through the whitelist dict.
- `/marketplace/listings/sets` must not leak `user_id`/email (only aggregate
  set counts).

## Tests
- New: `tests/marketplace/test_trade_queries.py` (unit, in-memory SQLite —
  copy the fixture style from `tests/marketplace/conftest.py`).
- Extend: `tests/marketplace/test_router.py` (listings sort + sets) and
  `tests/api/test_trade_match_router.py` (duplicates filters + sets). Follow the
  existing `TestClient` + `app.dependency_overrides[get_current_user]` pattern.

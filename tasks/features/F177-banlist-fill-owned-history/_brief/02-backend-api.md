# 02 — Backend API (grouped ban list, owned filter, status)

## Files
- NEW `src/database/banlist_queries.py` (F177-T04)
- EDIT `src/api/routers/banlist.py`, `src/api/schemas/banlist.py` (F177-T07)
- Tests: NEW `tests/banlist/test_banlist_queries.py`, NEW `tests/banlist/test_api_f177.py`;
  keep `tests/banlist/test_api.py` green (adjust assertions that depend on per-printing duplicates)

## banlist_queries.py contract (F177-T04)
Pure query functions that receive `engine` (no Repository edits, because repository.py is a batch hotspot):
```python
def list_banlist_grouped(engine, format: str, status: str | None = None,
                         search: str | None = None, user_id: str | None = None,
                         owned_only: bool = False, limit: int = 50, offset: int = 0
                         ) -> tuple[list[dict], int]:
    """Banned/restricted cards for `format`, ONE entry per lower(name_en).
    status None → both banned+restricted; else only that status (only 'banned'/'restricted' allowed;
    anything else → ValueError).
    Representative printing: an owned printing if user_id is given and owns one, else the lowest card_id.
    Each dict: card_id, name_en, name_pt, set_code, collector_number, format, status,
               effective_date, printings (int), owned (bool), owned_quantity (int).
    owned: user owns ANY printing with the same lower(name_en) (user_collection.name_en or linked card name)
           — match by card_id first (UserCollectionRow.card_id in group's card_ids), then name fallback.
    owned_only requires user_id (if user_id is None → return ([], 0)).
    Sort: banned before restricted, then name_en case-insensitive.
    Pagination applied AFTER grouping (fixes the old double-offset bug); total = grouped count."""

def get_banlist_status(engine) -> dict:
    """{last_synced_at: datetime|None (max card_legalities.updated_at),
        legalities_count: int, banned_count: int, restricted_count: int,
        history_count: int, formats: int}"""
```
Implementation hint: select the rows (CardLegalityRow JOIN CardRow) filtered by format +
status IN (...) + search (ilike on name_en/name_pt) and group them in Python (ban lists are
small: at most a few thousand printings). The owned lookup is one query on
`UserCollectionRow` filtered by `user_id`, returning `card_id`, `name_en`, `quantity`.

## Router changes (F177-T07)
`GET /api/v1/banlist`:
- New query params: `owned_only: bool = False`, `limit: int = Query(50, ge=1, le=500)`, `offset: int = Query(0, ge=0)`.
- Auth: `user: User | None = Depends(get_optional_user)` (import from `src.api.deps`, as
  in `src/api/routers/market.py:12,141`). `owned_only=true` with no user → **401**
  via `api_error(401, ErrorCode.<existing auth code>, "Login required for owned_only")`
  (use whichever auth ErrorCode already exists in `src/api/error_codes.py`).
- `status` must be one of banned/restricted or omitted; otherwise 422 (use `Literal["banned","restricted"] | None`).
- Uses `banlist_queries.list_banlist_grouped(db.engine, …, user_id=user.id if user else None)`.
- Response: `success_response(entries, total=total, offset=offset)`.

`BanListEntry` schema: add `printings: int = 1`, `owned: bool = False`, `owned_quantity: int = 0`
(additive, backward compatible).

NEW `GET /api/v1/banlist/status` → `ApiResponse[BanlistStatusSchema]` (public). Declare it
BEFORE `/card/{card_id}` routes. The new schema `BanlistStatusSchema` goes in `src/api/schemas/banlist.py`.

Unchanged: `/formats`, `/card/{id}`, `/card/{id}/history`, `/history`, `/impact/{id}`, `POST /sync`.
The `/history` endpoint stays (CollectionCardDetail and external callers use it); only the
**page** goes away.

## Frontend contract (consumed by F177-T08)
```ts
export interface BanListEntry { /* existing fields */ printings: number; owned: boolean; owned_quantity: number; }
export interface BanlistStatus { last_synced_at: string | null; legalities_count: number;
  banned_count: number; restricted_count: number; history_count: number; formats: number; }
fetchBanList({ format, status?, search?, limit?, offset?, ownedOnly? })  // ownedOnly → owned_only=true
fetchBanlistStatus(): Promise<ApiResponse<BanlistStatus>>              // GET /api/v1/banlist/status
```

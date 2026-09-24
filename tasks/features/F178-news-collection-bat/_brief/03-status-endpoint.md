# F178 — Component: read-only status endpoint

Files: `src/database/repository.py` (add ONE method inside the existing
"News feed (F166)" section, right after `upsert_news_item`),
`src/api/routers/news.py`, `tests/api/test_news.py`. Owner: F178-T03.

## Repository
```python
def get_news_status(self) -> dict:
    """Return {total_items, last_fetched_at, newest_published_at} (ISO or None)."""
```
Single query: `select(func.count(NewsItemRow.id), func.max(NewsItemRow.fetched_at), func.max(NewsItemRow.published_at))`.

## Router (`src/api/routers/news.py`)
```python
class NewsStatusResponse(BaseModel):
    total_items: int
    last_fetched_at: str | None = None
    newest_published_at: str | None = None

@router.get("/status", response_model=ApiResponse[NewsStatusResponse])
def get_news_status(user: User = Depends(get_current_user), repo: Repository = Depends(get_db)): ...
```
- Declare it next to `/unread-count` (GET routes; `/{news_id}/...` are POST, no clash).
- Router must NOT import `src.services.news_fetcher`, `httpx` or `feedparser` —
  enforced by a test (`AC6`): read `news.py` source and assert no such import,
  so Render never does network I/O for news.
- No change to `src/api/app.py` (router already registered at `/api/v1`).

## Frontend contract (consumed by T05, may be mocked before T03 lands)
`GET /api/v1/news/status` → envelope `{ data: { total_items: number, last_fetched_at: string|null, newest_published_at: string|null } }`.

# T03 -- OpenAPI App Metadata & Tag Descriptions

**Wave:** 0
**Depends on:** none
**Estimated effort:** small

## User Story

As a developer using the API, I want the `/docs` page to have a clear
project description and organized tag sections so that I can discover and
understand endpoints without reading source code.

## What to Build

Update `create_app()` in `src/api/app.py` to include rich OpenAPI metadata.

### App-level metadata

```python
app = FastAPI(
    title="TEDHC Market API",
    description=(
        "REST API for TCG market intelligence -- price tracking, "
        "collection management, portfolio analysis, and trading for "
        "Magic: The Gathering cards in the Brazilian market."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=_OPENAPI_TAGS,
)
```

### Tag descriptions

Define `_OPENAPI_TAGS` as a list of dicts matching FastAPI's `openapi_tags`
format. One entry per tag currently used in routers:

```python
_OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "Authentication -- register, login, token refresh, password management.",
    },
    {
        "name": "admin",
        "description": "Admin operations -- user management, system health, error logs.",
    },
    {
        "name": "cards",
        "description": "Card lookup, search, price history, and batch operations.",
    },
    {
        "name": "collection",
        "description": "User card collection -- add, remove, import, sync, portfolio.",
    },
    {
        "name": "decks",
        "description": "Deck management -- create, edit, card list, legality check.",
    },
    {
        "name": "credits",
        "description": "Credit balance, transactions, and bonus claiming.",
    },
    {
        "name": "market",
        "description": "Market analytics -- top movers, trending cards, arbitrage.",
    },
    {
        "name": "scans",
        "description": "Price scan execution and history.",
    },
    {
        "name": "schedules",
        "description": "Scheduled scan management (CRON-based).",
    },
    {
        "name": "catalog",
        "description": "Offline card catalog -- Scryfall-seeded card database with filters.",
    },
    {
        "name": "alerts",
        "description": "Price alerts and notifications.",
    },
    {
        "name": "achievements",
        "description": "User achievements and gamification.",
    },
    {
        "name": "marketplace",
        "description": "Shared collections and trade matching.",
    },
    {
        "name": "evaluations",
        "description": "Card evaluation watchlist for buy decisions.",
    },
    {
        "name": "banlist",
        "description": "Format legality and ban list tracking.",
    },
    {
        "name": "prices",
        "description": "Price data ingestion and manual entry.",
    },
    {
        "name": "exchange-rates",
        "description": "Currency exchange rates (USD/BRL).",
    },
    {
        "name": "database",
        "description": "Database backup, restore, and sync operations.",
    },
    {
        "name": "sets",
        "description": "MTG set listing.",
    },
]
```

## Dev Notes

- Only modify `src/api/app.py`. Do NOT touch any router files -- that is
  T05.
- Keep the `_OPENAPI_TAGS` list in alphabetical order or grouped
  logically (auth/admin first, then domain, then infra).
- The existing `tags=["..."]` on each router already matches these names.
  If any router uses a tag not in this list, add it.

## Testing

1. Test that `GET /openapi.json` returns a response with `info.title`,
   `info.description`, and `info.version` matching the new values.
2. Test that `openapi.json["tags"]` contains all expected tag names with
   non-empty descriptions.
3. Test that `/docs` returns 200 (Swagger UI loads).
4. Test that `/redoc` returns 200 (ReDoc loads).

Expected: ~4-5 tests.

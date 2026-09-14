# 03 — Liga link opens the wrong card

## Root cause (confirmed by code reading)

The Liga price and the Liga link are derived from DIFFERENT names:

| Path | Name used | File |
|------|-----------|------|
| Collection sweep (`liga-sweep`, push-all.bat) | `UserCollectionRow.name_en or name_pt` | `src/collectors/liga_sweep.py:43-48`, query `repository.get_cards_for_liga_scan` (~L2013-2023) |
| Refresh-liga endpoint | `entry.name_en or entry.name_pt` | `src/api/routers/collection.py` `POST /{entry_id}/refresh-liga` (~L1344-1470) |
| Catalog sweep | `CardRow.name_en` | `repository.get_catalog_cards_for_liga_scan` (~L2104-2120) |
| **Link** on collection detail (since F123) | `CardRow.name_en` (canonical) | `src/api/routers/collection.py:1636-1664` |

All fetches hit `_build_card_url(name)` =
`https://www.ligamagic.com.br/?view=cards/card&card={quote_plus(name)}&show=1`
(`src/providers/liga/provider.py:43`) and store the observation under
`liga_{card_id}` / `liga_{card_id}_foil`. When `entry.card_id` drifted
(entry name "Arcane Signet", CardRow "Dain, Dwarven King"), the price comes
from the entry-name page but F123 made the link use the CardRow name → the
link opens another card while the price is "right".

MYP never has this problem because the URL that was actually scraped is
persisted (`SourceCardRow.url`) and served as-is.

## Decision (ADR 0012)

Mirror MYP: **persist the URL the Liga price was actually fetched from, keyed
exactly like the price observation**, and serve it.

- **Why not add `source_cards` rows (`liga_{card_id}`)?** Many repository
  queries join `SourceCardRow` ⇄ `PriceObservationRow` on `external_id`
  and/or filter `source == "liga"` (e.g. `repository.py` ~L1042-1110 history
  joins, ~L1293 latest-by-source, ~L1672 priced coverage, ~L2114-2120 catalog
  sweep eligibility). New rows there would silently change price history,
  coverage counts and catalog-sweep eligibility. Too risky.
- **Why not `set`/`collector_number` params?** Unverified Liga support; cannot
  be tested offline. Rejected.
- **Chosen:** new table `liga_card_urls`, created by `create_all` (no migration,
  works on SQLite + Postgres), touched by no existing query.

### Model (`src/database/models.py`, append after `WishlistRow`)

```python
class LigaCardUrlRow(Base):
    """URL of the LigaMagic page a Liga price observation was scraped from (F124).

    Keyed by the same external_id as PriceObservationRow (liga_{card_id} or
    liga_{card_id}_foil) so link and price always refer to the same page.
    """

    __tablename__ = "liga_card_urls"

    external_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
```

Import it in `src/database/repository.py` import block with
`# noqa: F401 (needed for create_all)` like `WishlistRow`.

### Repository API (`src/database/repository.py`)

```python
def upsert_liga_card_url(self, external_id: str, url: str) -> None: ...
def get_liga_card_url(self, external_id: str) -> str | None: ...
```
Upsert via `dialect_insert(self.engine, LigaCardUrlRow).values(...)
.on_conflict_do_update(index_elements=["external_id"], set_={"url": ..., "updated_at": datetime.now()})`
(`src/database/compat.py:16`) — works on both dialects.

### URL helpers (`src/providers/liga/urls.py`, new, pure functions)

```python
LIGA_HOST = "www.ligamagic.com.br"

def build_liga_card_url(card_name: str) -> str
    # moved from provider._build_card_url; provider keeps _build_card_url as a thin alias
def is_valid_liga_card_url(url: str | None) -> bool
    # https scheme, netloc == LIGA_HOST (or "ligamagic.com.br"), query has view=cards/card
def liga_external_id(card_id: int, is_foil: bool) -> str
    # f"liga_{card_id}_foil" if is_foil else f"liga_{card_id}"
```

### Provider (`src/providers/liga/provider.py`)

- `_fetch_page` / `_fetch_page_sync`: after a successful `page.goto(...)`,
  store `self._last_page_url = page.url` (fallback to requested `url` when
  `page.url` is falsy). Reset to `None` at the start of each fetch.
- `_search_card_unlocked`: after parsing, set
  `prices["page_url"] = self._last_page_url if is_valid_liga_card_url(self._last_page_url) else url`.
  Early-return path in `search_card` (empty name) does not set it.
- Adding a key to the dict is safe: all Liga consumers use `.get("normal")`
  / `.get("foil")`. (`bulk_canonize.py`, `match_report.py`, `sync_collection.py`
  call `search_card` on the **MYP** provider — not affected.)
- Tests mock `_fetch_page` with `AsyncMock`; to test page_url, set
  `provider._last_page_url` inside a `side_effect` coroutine.

### Writers (record URL right after `insert_price_observations`)

Each writer already computes the external_id; call
`repo.upsert_liga_card_url(external_id, prices["page_url"])` only when
`is_valid_liga_card_url(prices.get("page_url"))`. Failures to record the URL
must be logged (`log.warning("liga_url_record_failed", ...)`) and NEVER fail
the price write.

| Writer | Location |
|--------|----------|
| Liga sweep | `src/collectors/liga_sweep.py` `_fetch_liga_price` (return url alongside observation) + loop (~L160-166) |
| Refresh-liga endpoint | `src/api/routers/collection.py` after `repo.insert_price_observations([obs])` (~L1455) |
| Card refresh (catalog detail) | `src/api/routers/cards.py` ~L308-332 |
| Liga scan collector | `src/collectors/scan.py` ~L50-80 |
| CLI | `src/cli/main.py` ~L1520-1540 |

### Readers

**Collection detail** (`src/api/routers/collection.py:1636-1664`, `_build_collection_detail`):
1. If `entry.card_id`: try `repo.get_liga_card_url(liga_external_id(card_id, is_foil))`;
   if foil and none, try the non-foil key.
2. Fallback: `build_liga_card_url(entry.name_en or entry.name_pt)` — the SAME
   name source the collection sweep/refresh uses (this intentionally reverts
   F123's CardRow-name preference for the link; the price is fetched by entry
   name, so the fallback link must be too).
3. If no name at all: `None`.
Only serve a stored URL if `is_valid_liga_card_url(url)`.

**Catalog card detail** (`src/api/routers/cards.py` `GET /cards/{card_id}`, ~L169-191):
add `ligamagic_url: str | None = None` to `CardDetail` schema
(`src/api/schemas/cards.py:32`); stored URL for `liga_{card_id}` else
`build_liga_card_url(card.name_en)`. Frontend `CardDetail.tsx:350` uses
`card.ligamagic_url ?? <current name-based href>`.

**Web search** (`src/api/routers/card_search.py:184`): use
`prices.get("page_url")` when valid, else `build_liga_card_url(card_name)`.

## Backfill

No network backfill (would re-scrape everything). URLs populate on the next
sweep/refresh of each card; until then the fallback link (entry name, same
as price fetch) is used. Document in README. Note: sweep skips cards whose
Liga price is newer than `max_age_days` (default 7), so full coverage takes
up to one sweep cycle.

## Existing tests impacted

- `tests/api/test_collection_liga_links.py` — asserts CardRow name is used;
  must be updated to the new contract (stored URL > entry name fallback).
  Mocks use `MagicMock()` repo → set `mock_repo.get_liga_card_url.return_value = None`
  explicitly (a bare MagicMock returns a MagicMock, which is truthy!).
- `tests/api/test_collection_detail.py` — same MagicMock gotcha.
- `tests/providers/test_liga_provider.py`, `tests/collectors/test_liga_sweep.py`,
  `tests/unit/test_liga_sweep_catalog.py`, `tests/unit/test_cli_catalog.py`,
  `tests/api/test_admin_f100.py` — verify still green; update mocks if
  `search_card` return shape assertions are strict (`==` on dict).

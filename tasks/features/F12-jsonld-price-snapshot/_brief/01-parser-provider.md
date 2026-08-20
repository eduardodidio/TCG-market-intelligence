# F12 Brief -- Parser and Provider (T01-T03)

## Domain Model (T01)

File: `src/domain/models.py`

New dataclasses:
- `JsonLdPrice`: price (Decimal | None), currency (str), availability (str)
- `SnapshotSummary`: total_entries, fetched, stored, skipped_existing,
  skipped_zero_price, errors, error_details, started_at, finished_at

## Parser (T02)

File: `src/parsers/myp.py`

New function: `parse_jsonld_price(html: str) -> JsonLdPrice | None`
- Reuses existing `parse_json_ld_product()` to find the Product JSON-LD
- Extracts `offers.price`, `offers.priceCurrency`, `offers.availability`
- Normalizes availability URL to short form ("InStock", "OutOfStock")
- Treats price=0 as None (no meaningful data)

## Provider (T03)

File: `src/providers/myp/provider.py`

New method: `fetch_current_price(product_id: str, slug: str) -> JsonLdPrice | None`
- URL: `BASE_URL/magic/produto/{product_id}/{slug}`
- Uses existing `_fetch()` for HTTP with retry + rate limiting
- Returns None on fetch failure (caught, not raised)

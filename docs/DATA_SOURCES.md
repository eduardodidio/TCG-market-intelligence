# Data Sources

## Overview

TCG Market Intelligence collects price data from Brazilian TCG marketplaces.
The system is designed around a provider abstraction (`CardSourceProvider` ABC)
that allows adding new sources without modifying core logic.

| Source | Status | Game | Provider Class |
|--------|--------|------|----------------|
| MYP Cards | Active | Magic: The Gathering | `MypCardsProvider` |
| Liga Magic | Planned | Magic: The Gathering | -- |
| Scryfall | Planned (metadata only) | Magic: The Gathering | -- |
| CardMarket | Planned | Multiple | -- |
| TCGPlayer | Planned | Multiple | -- |

---

## MYP Cards (mypcards.com)

### Domain and Anti-Bot Protection

- **Base URL:** `https://mypcards.com`
- **Cloudflare protection:** Active. Standard HTTP clients (httpx, requests)
  receive HTTP 403. The project uses **curl_cffi** with
  `impersonate="chrome"` to bypass Cloudflare's browser fingerprinting.
- **robots.txt:** Allows `User-agent: *` but explicitly blocks `ClaudeBot`.
  The `/api/` path is disallowed for all agents.

### URL Patterns

All URLs below are relative to `https://mypcards.com`.

| Purpose | Pattern | Example |
|---------|---------|---------|
| Editions list | `/magic/edicoes?page={1..N}` | `/magic/edicoes?page=3` |
| Set card listing | `/magic/{set-slug}?page={N}` | `/magic/dominaria-remastered` |
| Card product page | `/magic/produto/{id}/{slug}` | `/magic/produto/179334/tutor-esclarecido` |
| Price history | `/magic/preco/{id}/{slug}?dias={D}` | `/magic/preco/179334/tutor-esclarecido?dias=1095` |
| Search | `/produto/search?marca=magic&term={q}` | `/produto/search?marca=magic&term=lightning+bolt` |

**Price history `dias` parameter:** Accepted values are `30`, `90`, `180`,
`365`, and `1095` (3 years). The provider defaults to `1095` for maximum
historical coverage.

### Data Extraction Methods

#### JSON-LD (`@type: Product`)

Each card product page contains a `<script type="application/ld+json">` block
with a JSON-LD `Product` object. Fields extracted:

| JSON-LD Field | Usage |
|---------------|-------|
| `name` | Card name (typically PT-BR for translated cards) |
| `sku` | SKU string, parsed for set code and collector number |
| `productID` | MYP's internal product identifier |
| `offers.price` | Current minimum/average price (BRL) |
| `image` | Card image URL (language hint via `_en.jpg` / `_pt.jpg` suffix) |

A `BreadcrumbList` JSON-LD block on the same page may contain an alternate
card name (used to disambiguate EN vs PT names).

#### `window.precoChartConfig` JavaScript Variable

The price history page embeds chart data in a JS variable:

```javascript
window.precoChartConfig = {
  labels: ["01/01/2024", "08/01/2024", ...],   // DD/MM/YYYY dates
  series: [
    { key: "mediana", dados: [12.50, 13.00, ...] },
    { key: "tcg",     dados: [11.00, 12.00, ...] },
    { key: "ultimo",  dados: [10.00, 11.50, ...], meta: ["seller info", ...] },
    { key: "volume",  dados: [5, 3, ...] }
  ]
};
```

The parser (`src/parsers/myp.py::parse_price_history`) extracts this via regex
and maps each data point to a `HistoricalPrice` domain object.

#### TCG Price from Stats Section

A separate CSS-based extraction (`_extract_tcg_price`) scrapes the TCG Player
reference price from the card page's statistics section using the
`estat-tcg` CSS class.

### SKU Format

MYP SKUs follow the pattern `magic_{set}_{number}`, e.g., `magic_ltr_748`.

- `{set}` is a lowercase set abbreviation that maps to
  [Scryfall set codes](https://scryfall.com/sets) (uppercased: `LTR`).
- `{number}` is the collector number within that set.

The parser (`src/parsers/myp.py::parse_sku`) splits on `_` and returns
`(set_code.upper(), collector_number)`.

### Card Names

- **JSON-LD `name`** is typically the **Portuguese (PT-BR)** name for
  translated cards. For English-only printings, it is the English name.
- **English names** can be obtained via the search API
  (`/produto/search?marca=magic&term={q}`), which returns both EN and PT names.
- The parser uses heuristics (breadcrumb comparison, image URL language hints)
  to assign `name_en` and `name_pt` as accurately as possible.

### Rate Limiting

The provider enforces a configurable delay between requests:

| Config Field | Default | Description |
|-------------|---------|-------------|
| `delay_seconds` | `1.0` | Minimum delay between HTTP requests |
| `max_retries` | `3` | Maximum retry attempts per request |
| `timeout_seconds` | `30.0` | HTTP request timeout |
| `history_days` | `1095` | Default days of price history to fetch |
| `max_editions_pages` | `50` | Maximum edition list pages to crawl |

**Retry behavior:**
- **HTTP 429 (rate limited):** Exponential backoff starting at 10s, capped at 60s.
- **HTTP 403 (forbidden):** Exponential backoff starting at 20s, capped at 120s
  (likely Cloudflare challenge).
- **Other HTTP errors (4xx/5xx):** Exponential backoff (`2^attempt` seconds).
- **Timeouts / OS errors:** Same exponential backoff with retry.

### Known Limitations

- **Weekly resolution:** Historical price data points are spaced roughly one
  week apart, not daily.
- **Maximum history:** 1095 days (~3 years) is the longest window available.
- **PT-only names from JSON-LD:** The product page does not reliably provide
  English card names. Cross-referencing with the search API or Scryfall is
  needed for accurate EN names.
- **No official API:** All data is scraped from HTML pages; the site structure
  may change without notice.

---

## Planned Sources

### Liga Magic
Brazilian marketplace with card listings and price history. Will require its
own parser and provider implementation.

### Scryfall (Metadata Only)
[Scryfall](https://scryfall.com) provides a free REST API for card metadata
(Oracle text, set info, images, multilingual names). Not a price source, but
essential for enriching card identity data and mapping across sources.

### CardMarket
European marketplace (cardmarket.com). Potential source for international
price comparison.

### TCGPlayer
US marketplace (tcgplayer.com). Potential source for USD reference prices.

---

## Adding a New Source

To add a new data source:

1. **Implement the `CardSourceProvider` ABC** defined in
   `src/domain/interfaces.py`. The interface requires:

   ```python
   class CardSourceProvider(ABC):
       source_name: str                                        # property
       async def discover_sets() -> list[str]
       async def discover_cards(set_id: str | None) -> list[SourceCard]
       async def get_current_price(card: SourceCard) -> PriceSnapshot | None
       async def get_price_history(card: SourceCard, days: int) -> list[HistoricalPrice]
   ```

2. **Create a parser module** under `src/parsers/` for HTML/JSON parsing logic.
3. **Create a provider module** under `src/providers/<source_name>/`.
4. **Register the provider** in the CLI and collector modules.
5. **Add tests** with fixture HTML files under `tests/fixtures/`.
6. **Document the source** in this file following the MYP Cards section format.

See also: [DATABASE.md](DATABASE.md) for how source data maps to the schema.

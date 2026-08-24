# ADR-0006: LigaMagic as Price Provider

## Status

Accepted

## Context

MYP Cards price history is auth-walled (login required since 2026-08-20).
LigaMagic (ligamagic.com.br) is the primary Brazilian MTG price aggregator,
with marketplace pricing data for Normal and Foil variants across all
editions. We need to validate whether we can reliably extract price data
from LigaMagic using browser automation before committing to a full
provider implementation.

## Decision

Proceed with LigaMagic as a secondary price provider. The feasibility spike
(F57-T01) confirmed that browser automation via Playwright can reliably
extract price data from LigaMagic card pages.

## Findings

### HTTP Access

- **Status**: All 5 test cards returned HTTP 200 (no blocks, no 403s)
- **Cloudflare**: The word "cloudflare" appears in page HTML (likely a
  Cloudflare-proxied site), but no challenge pages were served during
  headless Chromium requests
- **Auth wall**: Login/cadastro links exist in the nav bar but price data
  is fully public -- no authentication required to view card prices

### Price Extraction

- **Regex approach**: `R\$\s*[\d.,]+` reliably captures all prices on the
  page. Every card returned 5+ price values.
- **CSS selector approach**: `[class*="price"]` captures the "Preco Medio
  de Venda no Marketplace" section with Normal and Foil prices clearly
  separated.
- **Data structure**: Each card page shows 3 price tiers per variant
  (Normal/Foil), corresponding to low/mid/high marketplace prices.
- **Page titles**: Include both PT and EN card names
  (e.g., "Raio / Lightning Bolt"), useful for name matching.

### Sample Prices Extracted

| Card          | Normal (low)  | Normal (mid)  | Normal (high) | Foil (low)    |
|---------------|---------------|---------------|---------------|---------------|
| Lightning Bolt| R$ 6,65       | R$ 12,79      | R$ 15,00      | R$ 18,95      |
| Counterspell  | R$ 24,00      | R$ 24,00      | R$ 24,00      | --            |
| Sol Ring      | R$ 9,95       | R$ 14,30      | R$ 22,00      | --            |
| Thoughtseize  | R$ 45,56      | R$ 62,86      | R$ 120,00     | R$ 117,30     |
| Fatal Push    | R$ 7,00       | R$ 9,30       | R$ 12,00      | R$ 7,99       |

### Performance

- **Average time per card**: 5.48 seconds (first card ~8.8s due to cold start)
- **Page sizes**: 587KB to 1.2MB (JS-heavy pages)
- **Acceptable for batch**: At 5.5s/card, scanning 350 cards takes ~32 minutes
  (with 4s rate-limit delays, ~55 minutes total)

### Dependencies

- `playwright>=1.40` (Python package, ~1MB)
- Chromium browser binary (~192MB, installed via `playwright install chromium`)
- Total disk footprint: ~307MB (Chromium + headless shell + ffmpeg)

### URL Pattern

```
https://www.ligamagic.com.br/?view=cards/card&card={name}&show=1
```

Card name is URL-encoded with `+` for spaces. The `show=1` parameter
ensures all editions are displayed.

### Risks

1. **Rate limiting**: No rate limiting was observed during the 5-card test,
   but aggressive scraping could trigger Cloudflare challenges. A 4-second
   delay between requests is recommended.
2. **Cloudflare escalation**: Cloudflare JS is present on the page. If
   LigaMagic enables stricter bot detection, headless Chromium may get
   blocked. Mitigation: use realistic user-agent, viewport, and locale
   settings (already implemented in spike).
3. **HTML structure changes**: Price extraction relies on CSS class names
   and regex patterns. LigaMagic UI updates could break the parser.
   Mitigation: test suite with known cards to detect breakage early.
4. **Dependency weight**: Playwright + Chromium adds ~307MB. This is
   acceptable for a server deployment but heavy for development
   environments. Consider making it an optional dependency.

## Consequences

### Positive

- We gain access to comprehensive Brazilian MTG marketplace pricing
  (Normal + Foil, low/mid/high tiers)
- LigaMagic covers far more cards than MYP Cards
- Price data is public (no auth required)
- PT + EN card names in page titles simplify card matching

### Negative

- Playwright + Chromium is a heavy dependency (~307MB)
- Browser automation is slower than HTTP API calls (~5.5s/card vs <1s)
- Fragile to HTML structure changes (no official API)
- Must respect rate limits to avoid Cloudflare blocks

### Next Steps

1. Implement `LigaMagicProvider` following `CardSourceProvider` ABC
2. Build a dedicated parser for LigaMagic HTML structure
3. Add LigaMagic as a price source in the scan pipeline
4. Consider edition-specific URL patterns for targeted scraping

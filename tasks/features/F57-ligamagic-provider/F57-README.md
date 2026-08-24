# F57 — LigaMagic Price Provider

**Status:** planned
**Priority:** medium
**Depends on:** none (independent of F56/F58)

## Summary

Add LigaMagic (ligamagic.com.br) as a new price data source for Magic
cards in the Brazilian market. LigaMagic becomes the primary source;
MYP becomes fallback.

## Feasibility Assessment

LigaMagic research findings (2026-08-24):

- **Anti-bot**: Direct HTTP requests get 403. curl_cffi alone insufficient.
- **No API**: Community has requested since 2014; none exists.
- **Requires browser automation**: Selenium/Playwright needed for JS rendering.
- **CSS obfuscation**: Price data uses obfuscated CSS classes.
- **URL pattern**: `?view=cards/card&card=[name]&show=1`
- **Community scrapers**: Multiple exist (Python/Selenium, Ruby/Capybara).
- **New dependency**: Playwright or Selenium (significant addition).

### Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Browser automation adds ~200MB dep | Medium | Use playwright (lighter than Selenium) |
| CSS obfuscation breaks parser | High | Version-pinned selectors + fallback |
| Rate limiting / IP ban | Medium | 3-5s delays, session reuse |
| Maintenance burden (2 providers) | Low | Shared ABC, provider registry |

## Tasks

| Task | Wave | Description |
|------|------|-------------|
| F57-T01 | 0 | Feasibility spike — validate scraping approach |
| F57-T02 | 1 | Provider skeleton + card search |
| F57-T03 | 1 | Price parser + snapshot integration |
| F57-T04 | 2 | Provider registry + fallback chain |
| F57-T05 | 2 | CLI + API integration |

## Wave Plan

- **Wave 0**: T01 — spike only (validate Playwright works, parse one card page)
- **Wave 1**: T02 + T03 in parallel (provider impl)
- **Wave 2**: T04 + T05 in parallel (integration)

## Acceptance Criteria

1. LigaMagic provider implements CardSourceProvider ABC
2. Can fetch current price for a card by name from LigaMagic
3. Provider registry selects LigaMagic as primary, MYP as fallback
4. CLI `scan` and API endpoints use the provider chain
5. Rate limiting respects 3-5s delay between requests
6. MYP continues to work as before (no regression)

## Decision Required

**User must confirm** adding Playwright/Selenium as a new dependency
before Wave 0 begins. This is a significant addition (~200MB).

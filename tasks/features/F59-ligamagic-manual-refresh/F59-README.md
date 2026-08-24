# F59 — LigaMagic Manual Refresh

**Status:** planned
**Priority:** P2
**Wave count:** 1 (3 tasks, all sequential due to backend→frontend dep)

## Summary

Expose the existing LigaMagic provider (F57) as a per-card manual refresh
option in the frontend. Users can click a "LigaMagic" button on the card
detail page to fetch the current price from LigaMagic when MYP fails or
when they want an independent price check.

## Context

- LigaMagicProvider already works (F57): Playwright headless, ~5.5s/card,
  `get_current_price()` and `search_card()` methods
- Currently only accessible via CLI (`--provider liga`)
- MYP is the default provider; Liga is a fallback
- Price history from Liga is not available (returns `[]`)
- The provider requires Playwright + Chromium (~307MB dep, already installed)

## User Story

**As a** collector,
**I want to** refresh a card's price from LigaMagic with one click,
**so that** I get an independent price reference when MYP has no data or
I want to cross-check prices.

## Acceptance Criteria

1. Card detail page shows a "LigaMagic" refresh button (distinct from MYP refresh)
2. Button triggers a backend call that uses LigaMagicProvider
3. Loading state shows spinner + "Fetching from LigaMagic..." message
4. On success: price updates, source badge shows "liga", success toast
5. On failure: error message (card not found, timeout, rate limit), no crash
6. PriceSourceBadge renders "LigaMagic" label for source="liga"
7. Timeout is generous (30s) since Playwright is slow
8. The button is only visible on cards that have a name (name_en or name_pt)

## Non-Goals

- Bulk LigaMagic refresh (too slow with Playwright, one at a time)
- Replacing MYP as default provider
- LigaMagic price history
- Liga source cards / canonical linking (just price snapshot)

## Architecture Notes

- New endpoint: `POST /collection/{entry_id}/refresh-liga`
- Uses LigaMagicProvider directly (not registry fallback chain)
- Stores price as source="liga" in price_observations
- No new DB models needed — reuses HistoricalPrice with source="liga"
- Frontend: new API function + button component on CollectionCardDetail

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| F59-T01 | Backend endpoint `POST /collection/{entry_id}/refresh-liga` | W1 |
| F59-T02 | Frontend API client + LigaMagic refresh button on card detail | W1 |
| F59-T03 | PriceSourceBadge "liga" support + i18n keys | W1 |

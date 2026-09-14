# ADR 0012 — Persist the fetched LigaMagic URL keyed by price external_id

**Status:** Accepted · **Date:** 2026-09-13 · **Feature:** F124

## Context

The collection card detail "Ver na LigaMagic" link opened a different card
than the one whose Liga price was shown. Liga prices are fetched by NAME
(`?view=cards/card&card={name}&show=1`) using `UserCollectionRow.name_en`
(collection sweep, refresh-liga) or `CardRow.name_en` (catalog sweep), and
stored as `liga_{card_id}[_foil]`. Since F123 the link was built from
`CardRow.name_en`; when `entry.card_id` drifted, price and link referenced
different pages. MYP does not have the issue because it persists the scraped
product URL in `source_cards.url`.

## Options

1. **Insert `source_cards` rows `liga_{card_id}` with the URL.** Rejected:
   several repository queries join `source_cards` ⇄ `price_observations` on
   `external_id` or filter `source='liga'` (price history, latest-by-source,
   coverage, catalog-sweep eligibility) — silent behaviour changes.
2. **Add set / collector number to the Liga URL.** Rejected: Liga support for
   such parameters is unverified and untestable offline.
3. **Build link from the same name as the fetch.** Partial: correct for
   collection sweep/refresh, but ambiguous when catalog sweep (CardRow name)
   wrote the latest observation.
4. **New table `liga_card_urls(external_id PK, url, updated_at)`**, written by
   every Liga price writer with the page URL actually loaded (`page.url`
   after Playwright navigation), read by detail endpoints. **Chosen**, with
   option 3 as fallback.

## Decision

Option 4 + fallback 3. Table created via `Base.metadata.create_all` (works on
SQLite and Neon PostgreSQL, no ALTER). URLs are validated (https,
`ligamagic.com.br` host, `view=cards/card`) before being stored or served.
Recording the URL never fails the price write.

## Consequences

- Link ⇄ price parity guaranteed for every price fetched after deploy.
- Cards not re-fetched yet use the name fallback (same name as collection
  sweep/refresh) until the next sweep (≤ `max_age_days`).
- One extra lightweight write per Liga price fetch.
- `_build_card_url` logic moves to `src/providers/liga/urls.py` (single source
  of truth for Liga URLs across provider, routers and seeder).

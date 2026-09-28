# F182 -- BanBadge Tooltip with Banned Formats

## Goal

Show which formats a card is banned or restricted in via a native browser
tooltip when hovering over the BanBadge on MyCollection card tiles. Users
currently must navigate to the card detail page to discover format-specific
legality information.

## Scope

Frontend-only change touching three areas:

1. **MyCollection.tsx** -- extend `bannedCardMap` to preserve per-format
   breakdown (already available from the API response) instead of discarding
   it during aggregation.
2. **BanBadge.tsx** -- accept an optional `formats` prop and render a
   `title` attribute listing each format and its status.
3. **i18n** -- add `banEngine.tooltipHeader` key in EN and PT-BR.

## Non-goals

- No backend changes (API already returns per-format data).
- No new npm dependencies.
- No changes to BanAlertBanner, CardDetail, or other pages.
- No custom tooltip component -- uses native `title` attribute.

## Acceptance Criteria

1. Hovering over a BanBadge on MyCollection shows a native tooltip listing
   all formats where the card is banned/restricted.
2. Tooltip text is internationalized (EN and PT-BR).
3. BanBadge works unchanged when `formats` is not provided (backward
   compatible).
4. Existing tests pass; new tests cover tooltip behavior.

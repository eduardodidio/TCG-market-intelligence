# F183 -- Card Detail Page: Prominent Ban/Legality Section

**Feature ID:** F183
**Status:** in-progress
**Date:** 2026-09-28

## Problem

Ban/legality data on the CollectionCardDetail page is buried at the bottom
(lines 684-692). Users must scroll past price charts, metadata, source links,
and delete buttons to discover if their card is banned. This is poor UX for
a high-signal piece of information that directly affects a card's playability
and market value.

## Goal

Elevate ban/legality visibility by:

1. Moving LegalityPanel higher in the layout (into the right column, after
   MetricsPanel).
2. Adding a prominent BannedFormatsSummary alert box near the top of the page
   when the card is banned or restricted in any format.
3. Grouping ban history events by format with sub-headings for easier scanning.

## Scope IN

- Reorder CollectionCardDetail sections (move LegalityPanel up)
- Add BannedFormatsSummary inline alert box (not a separate component file)
- Enhance BanHistorySection with format-grouped sub-headings
- i18n keys for summary box and format grouping (en + pt-BR)
- Tests for new rendering behavior

## Scope OUT

- No backend changes, no new API endpoints
- No BanBadge changes (F182 owns it)
- No BanAlertBanner changes (F181 owns it)
- No new npm dependencies

## Success Metrics

- Banned/restricted formats visible without scrolling on a 1080p viewport
- Summary box absent when card has no bans/restrictions
- Ban history events grouped by format for easier scanning

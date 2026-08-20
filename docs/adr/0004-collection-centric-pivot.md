# ADR-0004: Pivot to Collection-Centric Model

**Status:** accepted
**Date:** 2026-08-19
**Deciders:** Eduardo Rutkoski Didio

## Context

TCG Market Intelligence was originally designed as a generic market scanner
that discovers and tracks every Magic card available on MYP Cards. After
shipping F01-F09, the platform collected price data across multiple sets --
but the user only owns ~548 unique cards across ~25 sets. The dashboard
displayed aggregate market statistics for hundreds of cards the user does
not own, making the data noisy and impersonal.

The user wants to shift from "track the entire MYP catalog" to "track my
personal collection and give me intelligence about the cards I own." This
requires:

- A way to import the user's collection (CSV export from an external tool)
- A pipeline to match collection cards against MYP Cards listings
- Database cleanup to remove data for cards the user does not own
- Frontend adjustments so the dashboard shows collection-specific stats
  (total value, coverage, per-card images)

This is a single-user application. There is no multi-user requirement, and
the user is comfortable with CLI-driven workflows for import, match review,
cleanup, and sync operations.

## Decision

Pivot the platform from a generic market scanner to a **collection-centric
model** where:

1. The user's collection is the source of truth for which cards to track.
2. A `user_collection` table stores the imported collection with metadata
   (quantity, quality, language, rarity).
3. A **sync pipeline** searches MYP for each collection card, matches by
   SKU or name, fetches price history, and links the collection entry to
   the canonical `cards` table.
4. A **dry-run match report** lets the user review MYP coverage before
   committing to destructive operations (DB cleanup).
5. A **DB cleanup** operation removes cards, source_cards, and
   price_observations not linked to the user's collection -- preceded by
   an automatic SQLite backup.
6. The Dashboard shows **collection KPIs** (unique cards, total copies,
   estimated portfolio value, coverage percentage) instead of generic
   market stats as the primary view.
7. Card Detail pages display **Scryfall HD images** via the redirect API.

The existing generic market endpoints (`/api/v1/cards`, `/api/v1/market/*`)
remain functional but now operate on collection-scoped data after cleanup.

## Consequences

**Easier:**

- The dashboard immediately shows personally relevant data -- the user sees
  their collection value and price trends for cards they own.
- Database size shrinks significantly after cleanup (only collection cards
  remain), improving query performance and reducing sync time for updates.
- The sync pipeline is collection-driven: only ~548 cards need to be
  searched and tracked, versus thousands in a full market scan.
- The match report provides transparency before destructive operations,
  letting the user verify coverage and decide whether to proceed.
- Scryfall images dramatically improve the visual quality of the card
  browsing experience with zero storage cost (browser-fetched from CDN).

**Harder:**

- The platform loses the ability to discover new cards outside the user's
  collection. To track a new card, the user must update the CSV and
  re-import.
- DB cleanup is irreversible (though mitigated by automatic backup). If the
  user wants to return to full-market scanning, they need to re-run
  backfill from scratch.
- The matching pipeline depends on MYP's search API returning relevant
  results. Cards with unusual names or missing from MYP cannot be tracked.
- Single-user design means the architecture would need significant changes
  to support multiple users in the future (auth, per-user collections,
  data isolation).

## Alternatives Considered

- **Keep generic scanning, add collection overlay.** Track all cards but
  highlight collection cards in the UI. Rejected because it does not solve
  the noise problem (movers and stats still dominated by non-owned cards)
  and wastes bandwidth syncing cards the user does not care about.

- **Multi-user from the start.** Build authentication, per-user
  collections, and data isolation. Rejected as premature -- this is a
  personal tool with a single user. The complexity of auth, sessions, and
  data partitioning is not justified.

- **Scryfall as primary data source.** Use Scryfall's API for prices
  instead of MYP. Rejected because Scryfall does not have Brazilian market
  prices (BRL). MYP Cards is the only source for the Brazilian secondary
  market relevant to this user.

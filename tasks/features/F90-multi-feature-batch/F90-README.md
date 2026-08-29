# F90: Multi-Feature Batch

**Status:** planned
**Branch:** homol

## Overview

A batch of six independent improvements grouped by dependency order into
four parallel waves. Covers a schedule save bug fix, nav restructuring,
trending scope change, scheduled scan token cost enforcement, explore
cards web search, and an evaluation list (watchlist).

## Wave Plan

| Wave | Tasks | Dependencies |
|------|-------|-------------|
| 0 | T01 (Schedule Save Fix), T02 (Beta-Test Tab) | None -- parallel |
| 1 | T03 (Trending Collection-Only), T04 (Schedule Token Cost) | None -- parallel |
| 2 | T05 (Explore Cards Web Search) | None |
| 3 | T06 (Evaluation List / Watchlist) | Depends on T05 |

## Task List

| ID | Title | Wave | Status |
|----|-------|------|--------|
| F90-T01 | Schedule Save Fix | 0 | planned |
| F90-T02 | Beta-Test Tab Nav Grouping | 0 | planned |
| F90-T03 | Trending Collection-Only | 1 | planned |
| F90-T04 | Schedule Token Cost | 1 | planned |
| F90-T05 | Explore Cards Web Search | 2 | planned |
| F90-T06 | Evaluation List / Watchlist | 3 | planned |

## Sub-Feature Descriptions

- **F90a / T01** -- Schedule Save Fix: creating a new schedule from the
  admin panel silently fails. The backend endpoint works (returns 201),
  but the frontend does not reflect the new schedule. Root cause is in
  the response handling or error display, not the API client auth (which
  already sends JWT).

- **F90b / T03** -- Trending Collection-Only: trending gainers/losers
  currently rank ALL cards in the DB. Users only care about cards in
  their collection. Add user-scoped trending.

- **F90c / T05** -- Explore Cards Web Search: the Explore Cards page only
  shows cards already in the local DB. Add a web search flow that
  queries Liga for cards not yet in the system.

- **F90d / T06** -- Evaluation List (Watchlist): let users save cards from
  web search to an evaluation list for price tracking before deciding
  to add to collection.

- **F90e / T04** -- Schedule Token Cost: scheduled scans run without
  checking or deducting credit tokens. Enforce the token economy on
  automated scans.

- **F90f / T02** -- Beta-Test Tab: group experimental/beta nav items under
  a collapsible disclosure section to declutter the sidebar.

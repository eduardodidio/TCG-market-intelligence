# PRD: F20 -- Card Grid Size Control

**Status:** planned
**Created:** 2026-08-21
**Type:** frontend-only

## Problem

The collection grid uses a fixed card size (medium). Users with large
collections may want smaller cards to see more at once, while users who
want to admire artwork or read details may prefer larger cards. There is
no way to change this.

## Solution

Add a grid size control to the collection page header, letting users
switch between three sizes: Small, Medium (default), and Large. Persist
the preference in localStorage so it survives page refreshes and
sessions. In a future feature (post-F22), this preference may migrate to
the user profile on the backend.

## Grid Size Definitions

| Size   | Columns (responsive)                             | Gap  | Info section |
|--------|--------------------------------------------------|------|--------------|
| Small  | 3 / sm:4 / md:5 / xl:8                          | 3    | Compact (name + price only) |
| Medium | 2 / sm:3 / md:4 / xl:6 (current)                | 4    | Full (current layout) |
| Large  | 1 / sm:2 / md:3 / xl:4                          | 5    | Full (current layout) |

## UX Details

- Three icon buttons (grid-small, grid-medium, grid-large) placed in
  the collection page header, right-aligned, between filters and the
  card grid.
- Active button is visually highlighted (e.g., cyan border/bg).
- Default is Medium.
- Skeleton grid also respects the selected size.
- Transition between sizes should be smooth (CSS transition on grid
  template columns).

## Scope

- Frontend only. No backend changes.
- Applies to the My Collection page (`MyCollection.tsx`).
- Does NOT apply to the Explore/Cards page (can be extended later).
- localStorage key: `tcg:grid-size` with values `sm`, `md`, `lg`.

## Out of Scope

- Backend persistence (deferred to F22 user profiles).
- Custom card count per row / free-form slider.
- Applying to other grid pages (Explore, Dashboard movers).

## Success Criteria

1. User can toggle between 3 grid sizes.
2. Selection persists across page reloads.
3. Skeleton loading grid matches the selected size.
4. All existing card functionality (click, badges, prices) works at
   every size.
5. Responsive breakpoints work correctly at each size.

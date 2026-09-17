# F134 — Sidebar Scroll Fix

**Status:** planned
**Branch:** homol
**Created:** 2026-09-17

## Problem

The sidebar in `Layout.tsx` has no overflow handling or flex layout. When the
Beta Test disclosure section is expanded (adding up to 10 extra nav items on
top of 8 primary items), the sidebar content overflows the viewport and gets
clipped. The `mt-auto` on `InstallPrompt` is also ineffective because the
aside element is not a flex column container.

## Solution

Restructure the aside element into a flex column layout with two zones:

1. **Fixed header zone** (logo + user + controls) -- never scrolls.
2. **Scrollable nav zone** (`flex-1 overflow-y-auto`) -- contains primary nav
   items and Beta Test disclosure. Scrolls independently when content exceeds
   available height.
3. **Bottom-pinned InstallPrompt** -- `mt-auto` becomes effective with flex
   parent.

Add `tailwind-scrollbar` plugin for subtle scrollbar styling on the nav zone.

## Waves

| Wave | Task | Description |
|------|------|-------------|
| 0 | T01 | Sidebar flex layout + scrollable nav + scrollbar styling |

## Files Changed

- `frontend/src/components/Layout.tsx` -- flex layout restructure
- `frontend/tailwind.config.ts` -- add tailwind-scrollbar plugin
- `frontend/package.json` -- add tailwind-scrollbar dependency
- `frontend/src/components/__tests__/Layout.test.tsx` -- scroll/overflow tests

## Acceptance Criteria

- Sidebar content never overflows the viewport, regardless of Beta Test open/closed
- Logo, user section, and controls (TreasureBalance, AlertBell, CurrencyToggle,
  LanguageSelector, ThemeToggle) remain fixed at the top of the sidebar
- Nav section scrolls independently when it exceeds available height
- InstallPrompt is pinned to the bottom of the sidebar
- Works on mobile (fixed inset-y-0) and desktop (md:relative)
- Works in both collapsed and expanded sidebar states
- Scrollbar is subtle (thin, dark thumb, transparent track)

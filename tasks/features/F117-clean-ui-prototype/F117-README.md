# F117 — Clean UI Prototype (DeckCheck-inspired)

**Status:** planned
**Created:** 2026-09-09
**Branch:** homol

## Summary

Create a clean, dark-themed UI prototype inspired by deckcheck.co. Deployed
on a separate route prefix (`/v2/...`) so the current layout stays intact.
The user tests both versions side-by-side and decides whether to promote the
new layout.

Key design principles from deckcheck.co:
- Dark premium aesthetic (layered depth, subtle gradients)
- Clean typography (Figtree or Inter)
- Generous whitespace, fluid spacing (`clamp()`)
- Frosted-glass navigation (backdrop-filter: blur)
- Card-centric layout (cards are the hero, not tables)
- Minimal chrome, maximum content

## Wave Plan

| Wave | Tasks | Parallelism | Notes |
|------|-------|-------------|-------|
| 0 | T01, T02 | 2 parallel | Layout shell + design tokens (zero overlap) |
| 1 | T03, T04 | 2 parallel | Collection page + Dashboard page (use new layout) |
| 2 | T05 | 1 | Route switch + deploy on /v2 |

## Task List

| Task | Summary | Wave | Files |
|------|---------|------|-------|
| T01 | V2 Layout shell (sidebar, topbar, frosted glass) | 0 | LayoutV2.tsx (new), v2.css (new) |
| T02 | Design tokens + typography (Figtree, spacing, colors) | 0 | tailwind.config.ts, index.css |
| T03 | V2 Collection page (card grid, clean filters) | 1 | CollectionV2.tsx (new) |
| T04 | V2 Dashboard page (portfolio hero, movers, sparklines) | 1 | DashboardV2.tsx (new) |
| T05 | V2 route prefix + navigation toggle | 2 | App.tsx (add /v2 routes) |

## File Conflict Map

- **LayoutV2.tsx** — T01 creates (new file)
- **v2.css** — T01 creates (new file)
- **tailwind.config.ts** — T02 only (add design tokens)
- **CollectionV2.tsx** — T03 creates (new file)
- **DashboardV2.tsx** — T04 creates (new file)
- **App.tsx** — T05 only (add /v2 routes)
- **Existing files untouched** — prototype lives in parallel

## Design Decisions

1. **Separate route prefix** `/v2/` — no risk to existing UI
2. **Reuse existing API** — same backend endpoints, just new frontend views
3. **Reuse existing components** where possible (CardImage, badges, hooks)
4. **New layout only** — not rewriting business logic
5. **If user approves**, we promote v2 to default and archive v1

## Cross-Feature Parallelism

F117 is **fully independent** — all new files. Can run parallel with
F114, F115, F116. The only merge point is T05 adding routes to App.tsx
(trivial merge).

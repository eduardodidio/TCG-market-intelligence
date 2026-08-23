# F54 QA Report

**Feature:** Trending List Layout + Gaucho Orthography + Ticker Animation
**QA Agent:** Claude Opus 4.6
**Date:** 2026-08-23
**Test suite:** 963 tests passing (96 files), 0 failures

---

## Verdict: PASS

All three tasks meet their acceptance criteria. No regressions, no security issues, no broken imports.

---

## T01 -- Trending List Layout

### AC Validation

| Acceptance Criterion | Status | Evidence |
|---|---|---|
| Gainers/losers as two columns (grid-cols-2) on desktop, stacked on mobile | PASS | `Trending.tsx` line 82: `grid grid-cols-1 md:grid-cols-2 gap-6` |
| Each item is compact list row: name, set code, % change, price | PASS | `TrendingListItem.tsx`: flex layout with name+set badge left, change%+price right |
| No card images in list view -- text-only | PASS | `TrendingListItem` contains no `<img>` tags |
| Clicking row navigates to `/cards/:card_id` | PASS | `<Link to={/cards/${entry.card_id}}>` wraps entire row; test confirms `href="/cards/42"` |
| Period selector and limit selector still work | PASS | `Trending.tsx` unchanged controls; page tests verify period click and limit selector |
| TrendingSection accepts `variant` prop | PASS | `variant?: "cards" \| "list"` with default `"cards"` |
| Accessible: keyboard navigable | PASS | Uses `<Link>` (natively focusable), `title` attribute for truncated names |

### Backward Compatibility

- **Dashboard**: uses `TrendingSection` without `variant` prop -- defaults to `"cards"`, renders `TrendingCard`. No regression.
- **MarketPage**: uses `TrendingSection` without `variant` prop -- same default. No regression.
- Verified via grep: neither Dashboard nor MarketPage passes `variant` to `TrendingSection`.

### Test Coverage

- 10 tests for `TrendingListItem` (name, set badge, positive/negative change colors, BRL/USD/PILA formatting, link target, null set_code, hover class)
- 3 new tests for `TrendingSection` (default renders TrendingCard, `"cards"` renders TrendingCard, `"list"` renders TrendingListItem)
- 2 new tests for `Trending` page (grid layout classes, list variant rendering)

---

## T02 -- Gaucho Orthography Fixes

### AC Validation

| Acceptance Criterion | Status | Evidence |
|---|---|---|
| All gaucho strings use correct accents/spelling | PASS | Verified each string against spec table (see below) |
| Both locale files have identical gaucho sections | PASS | en.json lines 543-572 identical to pt-BR.json lines 543-572 |
| No code changes -- i18n JSON only | PASS | Only locale files modified |

### String-by-String Verification

| Key | Expected | Actual | Match |
|---|---|---|---|
| `gaucho.dashboard.message` | `ta` to `ta with accent`, `ne` to `ne with accent` | Correct accents applied | YES |
| `gaucho.collection.message` | `Tche` to `Tche with accent`, `Luxo` to lowercase, `gaucho` with accent, `colecao` with accent | All corrected | YES |
| `gaucho.collection.opt2` | `butias` to `butias with accent` | Accent applied | YES |
| `gaucho.collection.reply2` | `proxima` with accent, `na rateia` to `nao rateia`, `realese` to `release`, `muitos` to `muito` | All 4 fixes applied | YES |
| `gaucho.banlist.reply1` | `Ai` to `Ai with accent` | Accent applied | YES |
| `gaucho.banlist.reply2` | `Ai` to `Ai with accent`, `nao` with accent | Both accents applied | YES |
| `gaucho.decks.message` | `este` to `esse`, `ai` with accent, `gaucho` with accent | All corrected | YES |
| `gaucho.decks.opt2` | `nao` with accent | Accent applied | YES |
| `gaucho.decks.reply2` | `ta` with accent | Accent applied | YES |

---

## T03 -- Market Ticker Scroll Fix

### AC Validation

| Acceptance Criterion | Status | Evidence |
|---|---|---|
| Ticker scrolls continuously left-to-right | PASS | CSS `@keyframes ticker-scroll` with `translateX(0) to translateX(-50%)`, `linear infinite` |
| Animation is smooth and consistent | PASS | `will-change: transform` added for GPU compositing |
| Hovering pauses animation | PASS | `.animate-ticker:hover { animation-play-state: paused }` in index.css |
| `prefers-reduced-motion` disables animation | PASS | `@media (prefers-reduced-motion: reduce) { .animate-ticker { animation: none } }` |
| Ticker visible and populated when data exists | PASS | Returns null only when `loading` or `items.length === 0` |

### Speed Formula Verification

- **Old:** `Math.max(20, (items.length * 80) / 60)` -- 5 items = 20s (clamped), too slow
- **New:** `Math.max(10, (items.length * 60) / 60)` = `Math.max(10, items.length)` -- 5 items = 10s, 20 items = 20s
- Implementation matches spec exactly (`MarketTicker.tsx` line 14)
- Test assertions updated: 5 items = 10s, 20 items = 20s (both pass)

### CSS Changes

- `will-change: transform` correctly scoped to `.animate-ticker` only
- `--ticker-duration` CSS custom property fallback is 30s (sensible default)
- No unrelated CSS changes

---

## Cross-Cutting Checks

| Check | Result |
|---|---|
| Full test suite (963 tests, 96 files) | ALL PASS |
| No new dependencies added | Confirmed |
| Backward compat (Dashboard, MarketPage) | Confirmed -- neither passes variant prop |
| i18n parity (en.json == pt-BR.json gaucho) | Confirmed -- identical sections |
| Accessibility (keyboard nav, aria) | Links focusable, marquee role, aria-live=off, prefers-reduced-motion |
| No hardcoded strings outside i18n | Confirmed |
| No security concerns | N/A -- frontend-only, no auth changes |
| No broken imports | All 96 test files compile and pass |

---

## Observations (non-blocking, for backlog)

1. **Loading skeleton mismatch:** When `variant="list"`, the loading state still shows card-style skeletons. A row-based skeleton would be more visually consistent. Low priority since loading is transient.

2. **DRY opportunity:** `TrendingListItem.formatCurrency` is a local helper that duplicates currency formatting logic. Could be extracted to a shared utility if more list-style components are added.

---

**Final verdict: PASS -- ship it.**

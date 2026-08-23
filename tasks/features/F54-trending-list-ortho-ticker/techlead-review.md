# F54 Tech Lead Review

**Feature:** Trending List Layout + Gaucho Orthography + Ticker Animation
**Reviewer:** Tech Lead
**Date:** 2026-08-23
**Test suite:** 963 tests passing (96 files), 0 failures

---

## Verdict: APPROVED

All three tasks are well-implemented, backward-compatible, and adequately tested. No blockers found.

---

## T01 -- Trending List Layout

### What was done
- New `TrendingListItem` component: compact text-only row with card name, set badge, % change (color-coded), and price.
- `TrendingSection` gains an optional `variant` prop (`"cards" | "list"`, default `"cards"`).
- `Trending` page switches to `grid grid-cols-1 md:grid-cols-2` with `variant="list"`.

### Code quality: GOOD

1. **Backward compatibility is correct.** Dashboard and MarketPage do not pass `variant`, so they receive the default `"cards"` and continue rendering `TrendingCard` tiles. Verified via grep -- no regressions.

2. **Component design is clean.** `TrendingListItem` is a focused, single-responsibility component. It correctly uses `useCardName` for language-aware display, handles `null` set_code gracefully, and formats currency via a local helper.

3. **Accessibility is adequate.** Each row is a `<Link>`, which is natively keyboard-navigable and focusable. The `title` attribute on the name span provides the full name on truncation. The `hover:bg-slate-700/50` transition gives visual hover feedback.

4. **Minor observation (non-blocking):** The `formatCurrency` helper in `TrendingListItem` duplicates logic that likely exists elsewhere (e.g., `CurrencyIndicator`). This is acceptable for a leaf component but could be DRY'd in a future pass if currency formatting proliferates further.

5. **Minor observation (non-blocking):** The loading skeleton in `TrendingSection` always shows card-style skeletons regardless of variant. For the list variant, a simpler row skeleton would be more visually consistent. Not blocking since loading is transient.

### Test coverage: GOOD
- 10 tests for `TrendingListItem` covering: name render, set badge, positive/negative change colors, BRL/USD/PILA formatting, link target, null set_code, hover class.
- 3 new tests for `TrendingSection` covering variant switching (default renders TrendingCard, `"cards"` renders TrendingCard, `"list"` renders TrendingListItem).
- 2 new tests for `Trending` page verifying grid layout classes and list variant rendering.

---

## T02 -- Gaucho Orthography Fixes

### What was done
- Corrected accents and spelling in both `en.json` and `pt-BR.json` gaucho sections.

### Correctness: GOOD

All fixes from the task spec have been applied correctly:

| Key | Fix | Status |
|-----|-----|--------|
| `gaucho.dashboard.message` | `ta` -> `ta`, `ne` -> `ne` | Correct (accents applied) |
| `gaucho.collection.message` | `Tche` -> `Tche`, `ta o Luxo do gaucho` -> `ta o luxo do gaucho` | Correct |
| `gaucho.collection.opt2` | `butias` -> `butias` | Correct |
| `gaucho.collection.reply2` | `proxima na rateia` -> `proxima nao rateia`, `realese` -> `release`, `muitos` -> `muito` | Correct |
| `gaucho.banlist.reply1/reply2` | `Ai` -> `Ai` | Correct |
| `gaucho.decks.message` | `este` -> `esse`, `ai` -> `ai`, `gaucho` -> `gaucho` | Correct |
| `gaucho.decks.opt2` | `nao` -> `nao` | Correct |
| `gaucho.decks.reply2` | `ta` -> `ta` | Correct |

Both locale files contain identical gaucho sections, as required.

### Test impact
- `useGauchoEasterEgg.test.tsx` assertions updated to match corrected strings (e.g., `"luxo do gaucho"` with accent). All 11 hook tests pass.

---

## T03 -- Market Ticker Scroll Fix

### What was done
- Speed formula changed from `(items.length * 80) / 60` to `(items.length * 60) / 60`, simplifying to `items.length` seconds.
- Minimum duration lowered from 20s to 10s.
- `will-change: transform` added to `.animate-ticker` in `index.css` for GPU compositing.

### Code quality: GOOD

1. **Speed tuning is sensible.** With the old formula, 5 items produced ~6.7s but was clamped to 20s minimum -- far too slow. Now 5 items produces 10s (clamped), and 20 items produces 20s. The ticker will move at a visible, stock-exchange-like pace.

2. **`will-change: transform` is correctly placed.** Applied only to the `.animate-ticker` class, not broadly. This promotes the element to its own compositing layer for smoother 60fps animation.

3. **CSS structure is clean.** The `@keyframes`, `.animate-ticker`, hover pause, and `prefers-reduced-motion` media query are all properly layered.

4. **No files modified beyond scope.** `useTickerData.ts` and `TickerItem.tsx` are untouched, as planned.

### Test coverage: GOOD
- Duration calculation tests updated to match new formula: `max(10, (5*60)/60) = 10` and `max(10, (20*60)/60) = 20`.
- Existing tests for null/loading state, item doubling, aria attributes, responsive classes, and tabIndex all pass unchanged.

---

## Cross-cutting checks

| Check | Result |
|-------|--------|
| All 963 tests pass | Yes |
| No new dependencies added | Yes |
| Backward compat (Dashboard, MarketPage unaffected) | Yes -- neither passes `variant` prop |
| i18n parity (en.json == pt-BR.json for gaucho) | Yes |
| Accessibility (keyboard nav, aria) | Yes -- Links are focusable, ticker has `role="marquee"` + `aria-live="off"` |
| `prefers-reduced-motion` respected | Yes -- ticker animation disabled via media query |
| No hardcoded strings outside i18n | Yes |
| No security concerns | N/A (frontend-only, no auth changes) |

---

## Recommendations (non-blocking, for future backlog)

1. **DRY currency formatting.** `TrendingListItem.formatCurrency` could be extracted to a shared utility if more components need the same pattern.
2. **List-variant loading skeleton.** Consider a simpler row-based skeleton when `variant="list"` is active, for visual consistency during loading.

---

**Final verdict: APPROVED -- ship it.**

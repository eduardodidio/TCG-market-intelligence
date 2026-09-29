# F184 Tech Lead Review -- Auto-rotating Movers Ticker on Dashboard

**Reviewer:** Tech Lead
**Date:** 2026-09-29
**Verdict:** APPROVED

## Summary

Clean, well-structured implementation that faithfully follows the existing MarketTicker pattern. The MoversTicker and MoversTickerItem components are well-separated, tests are thorough (8 unit tests + 3 integration tests covering happy path, edge cases, accessibility, and DOM ordering), and both Mermaid diagrams and i18n keys are in place. One minor accessibility gap identified below.

## Issues Found

### 1. Duplicated items are keyboard-focusable (minor)

- **File:** `frontend/src/components/MoversTicker.tsx`, line 92-101
- **Description:** The items are duplicated for the seamless infinite loop (`[...items, ...items]`), but unlike `MarketTicker.tsx` (line 39), MoversTicker does not pass `tabIndex={index >= items.length ? -1 : undefined}` to the duplicated items. This means keyboard users tabbing through the ticker will encounter each card twice, which is confusing and a minor accessibility regression compared to the reference component.
- **Fix suggestion:** Add `tabIndex` prop to `MoversTickerItem` and pass `tabIndex={index >= items.length ? -1 : undefined}` in the map call, matching the MarketTicker pattern.

### 2. Duration formula simplifies to item count (minor)

- **File:** `frontend/src/components/MoversTicker.tsx`, line 72
- **Description:** `Math.max(10, (items.length * 60) / 60)` simplifies algebraically to `Math.max(10, items.length)`. With a max of 20 interleaved items, the duration would be 10-20 seconds. This is consistent with MarketTicker and works correctly, but the formula is misleadingly written as if the two `60` values represent different things (pixels per item vs. pixels per second). A comment clarifying the intent would help future readers.
- **Fix suggestion:** Add a brief inline comment, e.g. `// ~60px per item at ~60px/s scroll speed`.

## Positive Notes

- **Pattern consistency:** The implementation closely mirrors MarketTicker's structure (CSS class reuse, `[...items, ...items]` duplication, `motion-reduce` classes, `role="marquee"`, `aria-live="off"`), making the codebase predictable and maintainable.
- **Component decomposition:** Extracting `MoversTickerItem` as a separate presentational component is a good separation of concerns and makes both components independently testable.
- **Interleave logic:** The `interleave()` helper correctly handles uneven gainer/loser arrays, and the test verifies the exact ordering (gainer1, loser1, gainer2, loser2).
- **Self-contained data fetching:** The component fetches its own data and returns `null` on loading/empty/error, meaning the Dashboard does not need any conditional logic around it. This is the right pattern for a non-critical UI element.
- **Test quality:** 8 focused test cases for the component plus 3 Dashboard integration tests that verify presence, absence, and DOM ordering relative to KPIs. The test for `compareDocumentPosition` to verify layout order is a nice touch.
- **Diagrams:** Both Mermaid files are syntactically valid and accurately represent the data flow and user journey. The architecture diagram correctly shows the full stack from Dashboard down to the database.
- **Dark mode:** The color scheme (`bg-slate-800/80`, `border-slate-700`, `text-slate-200`, `text-emerald-400`, `text-red-400`) is inherently dark-mode compatible and consistent with the existing UI palette.

# F113 Tech Lead Review

**Reviewer:** Tech Lead Agent
**Date:** 2026-09-08
**Commits reviewed:** 539e4dd, ccae718, 2b83ba5, 15fccad, 80ec616, fd2a281, 48adb48, 6a58643 (+ 2 merge commits)

---

## Per-Task Assessment

### T01 - README "Future" cleanup (539e4dd)
Trivial docs cleanup. 6 insertions, 8 deletions. Shipped items removed from roadmap. **OK.**

### T02 - Catalog page URL fix + rarity filter + price sort (ccae718)
Frontend hooks correctly updated from `/api/catalog/` to `/api/v1/catalog/`. Rarity filter now supports comma-separated multi-select with parameterized SQL (no injection risk). Price sort properly handled with null-to-end logic on backend. Sort state synced to URL params. **OK.**

### T03 - Auth redirect + nav restructure (2b83ba5)
Clean approach: single `ProtectedRoute` wrapping the Layout route, removing redundant per-route wrappers. Public `/marketplace/share/:code` correctly extracted as a separate route block with its own Layout. Achievements and marketplace moved to BETA_NAV. Layout tests updated. **OK.**

### T04 - Web search PT/EN name fallback (ccae718)
`_find_alternate_name` does a case-insensitive lookup against local Scryfall catalog. Retry logic for both Liga and MYP providers is correct: no extra credit deduction on retry, failures return empty (no raise). 199 lines of test coverage including edge cases. **OK.**

### T05 - Project cleanup (15fccad)
Removed 6 unused agent prompt files (674 lines of dead code). Stale worktrees cleaned. No source code affected. **OK.**

### T06 - Set completion UX (fd2a281)
`SetCompletionSection` wrapper with localStorage-persisted collapse state, Scryfall SVG icons with fallback, click-to-navigate with keyboard accessibility (Enter/Space). Proper `role="button"` and `tabIndex={0}` attributes. 21 tests. **OK.**

### T07 - Portfolio/Liga data flow fix (48adb48)
Four distinct bugs fixed:
- **Bug A (foil backfill):** `_load_card_external_ids` and `_find_nearest_observation` now handle `liga_{id}_foil` patterns. Foil patterns inserted at priority position. Correct.
- **Bug B (priced count):** `get_collection_summary` expanded to check direct Liga/manual patterns via `IN` query. Card ID extraction from `external_id` uses replace+int parse with try/except safety net. Correct.
- **Bug C (empty state):** PortfolioDashboard shows message when `history.length <= 1`. Correct.
- **Bug D (movers):** `get_trending_price_data_for_user` now queries direct patterns in addition to source_cards join. Deduplication via same-date max-price logic preserved. Correct.
505 lines of backend tests + 190 lines of frontend tests. **OK.**

### T08 - CLAUDE.md placeholders (80ec616)
Mission, architecture, and commands sections updated from placeholder text to real content. Accurate description. **OK.**

### T09 - Cards page scroll reset, set icons, price refresh (6a58643)
- **Scroll reset:** `window.scrollTo({ top: 0, behavior: "smooth" })` on filter/sort change. Also added to MyCollection. Correct.
- **Set icons:** `scryfallSetIconUrl()` used in FilterChips via optional `icon` property. Clean extension.
- **Per-card refresh:** `POST /api/v1/cards/{card_id}/refresh-price` endpoint with credit guard, provider resolution from app state, proper error mapping (404, 402, 429, 502, 503). Price stored as `liga_{card_id}` observation. CardTile overlay button with hover reveal. 8 backend tests covering success, errors, credit deduction, DB storage.
- **Refresh All:** CreditConfirmModal with sequential progress, abort ref, credit refetch after completion. **OK.**

---

## Issues Found

### Minor (non-blocking)

1. **Redundant except clause (T04):** `except (asyncio.TimeoutError, Exception)` -- `Exception` already covers `asyncio.TimeoutError`. Harmless but noisy. Cosmetic only.

2. **No frontend tests for T09 components:** The Cards.tsx changes (Refresh All button, progress indicator) and CardTile refresh button have no frontend component tests. Backend endpoint is well-covered (8 tests), but the frontend interaction paths (modal flow, progress display, abort) are untested. This is acceptable given the backend coverage, but should be noted for a future pass.

3. **Credit deducted even when no price found (T09):** The refresh-price endpoint deducts credit even if Liga returns no price (empty normal/foil). This is consistent with how other refresh endpoints work in this codebase (pay for the attempt), so it is intentional, but could surprise users.

4. **`_find_alternate_name` bypasses Repository pattern (T04):** Opens a raw `Session(repo.engine)` instead of using a repository method. This is a pragmatic shortcut for a read-only lookup and does not cause correctness issues, but diverges from the established data access pattern.

### None Critical

No security issues, no data integrity bugs, no regressions detected.

---

## Security Checklist

- [x] Auth redirect covers all routes (single ProtectedRoute at Layout level)
- [x] Public route (`/marketplace/share/:code`) correctly excluded from auth
- [x] Credit deduction on refresh-price endpoint (check before, deduct after)
- [x] No auth bypass introduced
- [x] Parameterized SQL for rarity filter (no injection)
- [x] No hardcoded secrets

## Data Integrity Checklist

- [x] Foil backfill correctly resolves `liga_{id}_foil` patterns
- [x] Priced count includes Liga/manual direct patterns
- [x] Trending data includes direct patterns with deduplication
- [x] Price observations stored with correct external_id format

---

## Verdict: APPROVED

All 9 tasks deliver correct, well-tested changes that follow existing patterns. The auth consolidation (T03) is a clean simplification. The portfolio/Liga fixes (T07) are thorough and well-tested with 19 new tests. The refresh-price endpoint (T09) follows established credit patterns. Minor nits noted above do not warrant rejection.

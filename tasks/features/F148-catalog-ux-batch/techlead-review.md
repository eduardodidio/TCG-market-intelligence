# F148 — Catalog UX Batch: Tech Lead Review

**Reviewer:** Tech Lead Agent
**Date:** 2026-09-18
**Verdict:** APPROVED (with minor findings)

---

## Summary

F148 delivers five catalog improvements across two waves: default price-desc sort (T01), duplicate card disambiguation (T02), unpriced card refresh UX (T03), bulk collection price refresh (T04), and Liga URL import (T05). The implementation is clean, follows existing patterns, and has solid test coverage. All 32 backend tests and 9 frontend tests pass. One atomicity issue was found in T05 that should be addressed in a follow-up but does not block shipping.

---

## Per-Task Review

### T01 -- Default sort by price desc

**Files:** `frontend/src/pages/CatalogPage.tsx` (lines 417-419), `src/api/routers/catalog.py` (lines 239-241)

- Default sort state correctly changed to `sort_by: "price"`, `sort_dir: "desc"`.
- NULLS LAST already handled via `CASE WHEN po.median_price IS NULL THEN 1 ELSE 0 END` (catalog.py line 240). Works on both SQLite and PostgreSQL.
- URL param sync at line 434-435 correctly omits defaults (`price`/`desc`) from the URL, keeping URLs clean.
- `handleClearFilters` (line 544-545) correctly resets to `"price"` / `"desc"`.

**Verdict:** No issues.

---

### T02 -- Duplicate card disambiguation

**Files:** `frontend/src/pages/CatalogPage.tsx` (lines 239-257)

- Collector number rendered as `#collector_number` with `data-testid="collector-number"` (line 243).
- Type line rendered as truncated secondary text with `data-testid="type-line"` (line 253).
- Both fields gracefully handle null values (conditional rendering).
- Layout matches the spec: `[SET] [R] #354` then type line below.

**Verdict:** No issues.

---

### T03 -- Enqueue price fetch UX

**Files:** `frontend/src/pages/CatalogPage.tsx` (lines 128-129, 277-282)

- `isUnpriced` flag at line 128 drives always-visible behavior.
- `showAlwaysVisible` at line 129 includes `isUnpriced`, making the refresh button permanently visible for cards without prices.
- "Click to fetch price" hint text at lines 277-281 provides clear CTA for unpriced cards.
- Existing polling/feedback states (queued, completed, failed) continue to work correctly.

**Verdict:** No issues.

---

### T04 -- Bulk refresh collection prices

**Files:**
- `src/api/routers/collection.py` (lines 1985-2081)
- `frontend/src/pages/MyCollection.tsx` (lines 343-344, 458-472, 913-931, 1089-1100)
- `frontend/src/api/collection.ts` (lines 297-312)
- `tests/api/test_collection_refresh_all_prices.py` (10 tests)
- `frontend/src/pages/__tests__/MyCollectionQueueRefresh.test.tsx` (4 tests)
- `frontend/src/i18n/locales/en.json`, `pt-BR.json` (3 keys each)

**Architecture:**
- Endpoint follows the same queue-based pattern as `/catalog/scan`: fetch card IDs, deduplicate against 24h pending requests, credit guard, deduct, insert rows.
- Safety cap at 500 cards (`MAX_BULK_REFRESH_CARDS`) matches the daily-scan limit.
- Credit deduction happens only for cards actually enqueued (not skipped), which is correct.
- Empty collection returns early with `card_count: 0` without deducting credits.

**Frontend:**
- Button styled distinctly (amber vs cyan) to differentiate from the existing per-card refresh.
- CreditConfirmModal correctly shows `Math.min(summary.total_unique, 500)` as cost.
- Success feedback uses `alert()` (line 466) -- functional but not as polished as a toast. Acceptable for now.

**Tests:**
- Backend: 10 tests covering happy path, dedup, skip pending, old pending, 500-card cap, insufficient credits, credit deduction verification, empty collection, all-skipped scenario. Thorough.
- Frontend: 4 tests covering button rendering, empty-collection hiding, modal opening, and API call on confirm.

**Verdict:** No blocking issues. The `alert()` for success feedback is a minor UX debt.

---

### T05 -- Import card via Liga link

**Files:**
- `src/providers/liga/url.py` (lines 39-69)
- `src/api/routers/catalog.py` (lines 511-586)
- `frontend/src/pages/CatalogPage.tsx` (lines 319-389)
- `frontend/src/api/catalog.ts` (lines 11-26)
- `tests/unit/test_parse_liga_url.py` (13 tests)
- `tests/api/test_catalog_import_liga.py` (9 tests)
- `frontend/src/pages/__tests__/ImportLigaLink.test.tsx` (5 tests)
- `frontend/src/i18n/locales/en.json`, `pt-BR.json` (4 keys each)

**Architecture:**
- `parse_liga_card_url` is well-placed in `src/providers/liga/url.py` alongside the existing `liga_url_for_card_name`. Clean symmetry (build URL / parse URL).
- URL validation via `urlparse` + domain check + query param extraction is correct.
- Card search uses `ilike()` for case-insensitive matching (line 545), which works on both SQLite and PostgreSQL.
- When card is not found, a new `CardRow` is created with minimal data (name, set_code, game). This is reasonable -- the price request processor will fill in details later.

**Security:**
- Domain validation (`"ligamagic.com.br" not in hostname`) prevents arbitrary URL injection.
- Card name is extracted via `parse_qs` + `unquote_plus`, which handles URL encoding safely.
- No raw SQL -- the search query uses SQLAlchemy ORM with parameterized queries.
- Auth required (`get_current_user` dependency).

**Tests:**
- URL parser: 13 tests covering basic, with edition, encoded chars, DFC double slash, extra params, uppercase edition, invalid domain, missing/empty/blank card param, http scheme, subdomain, empty edition. Very thorough.
- API: 9 tests covering existing card queue, price request creation, new card creation, no set code, invalid URL, missing card param, credit deduction, insufficient credits, case-insensitive match.
- Frontend: 5 tests covering rendering, input/button, URL validation, button enable, success feedback.

---

## Cross-Cutting Findings

### FINDING-1: Credit deduction order in import-liga (Severity: Low)

**Location:** `src/api/routers/catalog.py`, lines 575-578

The `/import-liga` endpoint commits the database transaction (line 575) BEFORE deducting the credit (line 578). If the credit deduction call fails (network error, DB issue), the price request row exists but no credit was charged. This is inconsistent with the `/scan` endpoint (line 467), which deducts credits UPFRONT before inserting rows.

**Impact:** Low. The credit service uses the same DB engine, so failures are unlikely. The `check_sufficient` guard at line 536 ensures the user has credits. But for consistency and correctness, the deduction should happen before the commit, or both should be in the same transaction.

**Recommendation:** Move `credit_svc.deduct()` inside the `with Session` block, before `session.commit()`. This can be done in a follow-up patch.

### FINDING-2: Missing i18n key (Severity: Trivial)

**Location:** `frontend/src/pages/CatalogPage.tsx`, line 279

The key `catalog.clickToFetch` is used with a `defaultValue` fallback but is not present in either `en.json` or `pt-BR.json`. The English default ("Click to fetch price") works, but Portuguese users will see English text.

**Recommendation:** Add `"clickToFetch": "Clique para buscar preco"` to `pt-BR.json` and `"clickToFetch": "Click to fetch price"` to `en.json` under the `catalog` section.

### FINDING-3: No deduplication on import-liga (Severity: Trivial)

**Location:** `src/api/routers/catalog.py`, lines 567-575

The `/import-liga` endpoint does not check for existing pending `PriceUpdateRequestRow` entries before creating a new one. If a user pastes the same Liga URL twice within 24 hours, two pending requests will be created for the same card, each costing 1 credit. Both `/scan` and `/refresh-all-prices` deduplicate against pending requests.

**Impact:** Minimal. Users are unlikely to paste the same URL repeatedly, and the price processor handles duplicates gracefully. But for consistency, a dedup check would be cleaner.

---

## Checklist

| Criterion | Status | Notes |
|-----------|--------|-------|
| Architecture patterns | PASS | Follows existing queue-based price request pattern |
| API consistency | PASS | Endpoints use standard envelope response, proper error codes |
| Security | PASS | Auth enforced, URL validated, parameterized queries |
| Performance | PASS | No N+1 queries, batch inserts, safety caps |
| Error handling | PASS | ValueError caught, credit guards, empty collection handled |
| Tests | PASS | 32 backend + 9 frontend tests, all passing |
| i18n | PASS (minor gap) | Both locales updated; one key uses defaultValue only |
| Code quality | PASS | Clean diffs, no dead code, consistent style |
| Build | PASS | TypeScript compiles (pre-existing errors in unrelated test file) |

---

## Verdict: APPROVED

All five tasks are implemented correctly, follow existing patterns, and have adequate test coverage. The three findings above are low/trivial severity and do not block shipping. FINDING-1 (credit deduction order) should be addressed in the next hardening batch.

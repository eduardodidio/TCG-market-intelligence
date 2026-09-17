# F131 — Catalog UX Evolution: Tech Lead Review

**Reviewer:** Tech Lead
**Date:** 2026-09-17
**Verdict:** APPROVED WITH FINDINGS

---

## Summary

F131 delivers five tasks across two waves, bringing the catalog page to
near-parity with the collection page in interactivity. The implementation
is solid: grid size toggle reuses existing components correctly, per-card
refresh faithfully mirrors the CardTile pattern (with the addition of
proper polling feedback), bulk scan has a well-designed backend endpoint
with credit guards and deduplication, search is now cross-dialect
case-insensitive, and the FF set research is thorough with corrected
Scryfall codes.

Frontend builds cleanly. All 9 backend tests and 22 frontend tests pass.
The code quality is high overall, with a few findings that warrant
attention before or shortly after merge.

---

## Findings by Task

### T01 -- Grid Size Toggle on Catalog Page

**Status:** PASS

- Correctly imports and uses `useGridSize`, `GridSizeToggle`, and
  `GRID_SIZE_CONFIG` from existing shared modules.
- Both skeleton grid (line 668) and card grid (line 754) use the dynamic
  `GRID_SIZE_CONFIG[gridSize].gridClasses` -- consistent.
- `compact` prop is properly threaded to `CatalogCardTile` (line 758)
  and used to conditionally hide the info section (line 217:
  `{!compact && (...)}`).
- The toggle shares the same `localStorage` key (`tcg:grid-size`) as the
  collection page, providing cross-page UX consistency. This is the
  correct decision.
- Tests verify both compact mode hiding and the GridSizeToggle rendering.

**No issues found.**

---

### T02 -- Per-Card Liga Refresh Button on Catalog Tiles

**Status:** PASS

- The refresh button implementation in `CatalogCardTile` faithfully
  mirrors `CardTile.tsx`: same `refreshCardPrice` API call, same
  `data-testid` pattern (`refresh-card-price-{id}`), same event
  propagation prevention, same auth guard.
- Goes beyond the CardTile pattern by integrating `usePriceRequestPolling`
  for real-time feedback (queued -> polling -> completed/failed/timeout
  states). This is a nice improvement.
- Visual states are comprehensive: refresh icon, spinner (during API
  call), animated spinner (during polling), check (completed), X (error/
  failed), clock (polling timeout).
- Button is hidden for unauthenticated users (line 160-161).
- Tests cover: auth/unauth rendering, API call, disabled state after
  queue, API error, and network error (6 tests).

**No issues found.**

---

### T03 -- Refresh All Set (Backend + Frontend)

**Status:** PASS WITH FINDINGS

#### Backend (`src/api/routers/catalog.py`)

**Good:**
- Endpoint properly requires authentication (`get_current_user`).
- Set code is normalized to lowercase (line 404).
- Set existence is validated before proceeding (404 if not found).
- Max card cap at 1000 prevents abuse (line 427-433).
- Credit check and deduction happen before insertion.
- Deduplication against pending requests within 24h prevents waste.
- `session.add_all()` is used for bulk insertion -- efficient.

**Finding 1 (Low -- Unused Parameter):**
`CatalogScanRequest.max_age_days` (line 79, default=7) is declared in
the request schema but never referenced in the endpoint logic. The
deduplication window is hardcoded to 24 hours (line 444). This dead
field should either be removed from the schema or wired into the
deduplication logic as intended.

**Finding 2 (Medium -- Non-Atomic Credit + Insert):**
Credits are deducted on line 441 via `credit_svc.deduct()`, which
opens its own session internally. The `price_update_requests` rows are
inserted in a separate `Session` block (lines 446-474). If the insert
phase fails (e.g., DB error after deduction), credits are lost without
any requests being created. This is a known pattern in the codebase
(the per-card refresh has the same structure), but for bulk operations
involving potentially hundreds of credits, the risk is higher. Consider
wrapping both operations in a single transaction or adding a
compensating refund on insert failure. Not blocking for this review
since the pattern is established, but worth a follow-up.

**Finding 3 (Low -- Misleading Count):**
`queued_count` on line 470 increments for ALL cards, including those
that were deduplicated (skipped). The response `card_count` therefore
reports the total set size, not the number of newly queued requests.
The frontend feedback message says "Queued {{count}} cards..." which is
technically inaccurate when some were deduped. However, since the user
is charged for all cards regardless, reporting the total is arguably
the right UX choice. Consider renaming the field or adjusting the
messaging to be more precise (e.g., "Processing {{count}} cards, {{new}}
newly queued").

#### Frontend

**Good:**
- `frontend/src/api/catalog.ts` is clean and focused: single function,
  correct URL, 30s timeout for a potentially slow bulk operation.
- `CreditConfirmModal` integration shows cost and card count correctly.
- The button only appears when a set is selected AND user is
  authenticated.
- Feedback messages (success + error) auto-clear after 8 seconds.
- Credits are refetched after successful scan.
- i18n keys are present in both en.json and pt-BR.json.

**Tests (10 frontend):** Comprehensive -- covers rendering conditionals,
modal open/close, API call, success/error feedback, and credit refetch.

---

### T04 -- Catalog Search Coherence Review

**Status:** PASS

- The search filter now uses `LOWER()` wrapping (line 189):
  ```sql
  (LOWER(c.name_en) LIKE LOWER(:name) OR LOWER(c.name_pt) LIKE LOWER(:name))
  ```
  This is the correct cross-dialect approach -- works on both SQLite and
  PostgreSQL. Using `ILIKE` (PG-only) was correctly avoided.
- Search placeholder updated to bilingual hint
  (`catalog.searchPlaceholderBilingual`).
- Empty state messaging enhanced with language-switch suggestion
  (`catalog.emptySearchHint`), rendered when a name filter is active
  and results are empty (line 684-685).
- i18n keys are present in both locale files.

**Finding 4 (Low -- No Backend Tests for Search):**
The task spec called for `test_catalog_search.py` with 4 test cases
(case-insensitive matching, Portuguese name matching, empty string,
nonexistent name). No such test file was created. The `LOWER()` fix is
simple and correct, but having backend tests would prevent regression
if the search logic is modified later. Consider adding these in a
follow-up.

---

### T05 -- Final Fantasy Set Scan

**Status:** PASS

- Research is thorough: all 7 FF-related Scryfall set codes are
  documented with card counts, types, and release dates.
- Critical correction from the initial spec: actual codes are `fin`/`fic`
  (not `fft`/`ffc` as originally assumed). This is well-documented in
  the Research Findings section.
- Liga set code mappings verified -- no new mappings needed.
- Existing `CARD_SIGLA_OVERRIDES` already handles the `("fic", "120")`
  edge case.
- Operational steps are clearly documented for the user to execute
  (catalog seed + catalog scan commands).
- This is correctly treated as an operational task, not a code change.

**No issues found.**

---

## Documentation Compliance

**Finding 5 (Medium -- Missing Diagrams):**
Per CLAUDE.md, every feature MUST produce or update at least two Mermaid
diagrams under `docs/diagrams/`: an architecture diagram and a user
journey diagram. No `F131-architecture.mmd` or `F131-journey.mmd` files
exist. This should be addressed before marking the feature as shipped.

---

## Test Coverage Summary

| Layer | Test File | Count | Verdict |
|-------|-----------|-------|---------|
| Backend | `tests/api/test_catalog_scan.py` | 9 | PASS (all pass) |
| Frontend | `CatalogCardTile.test.tsx` | 12 | PASS (all pass) |
| Frontend | `CatalogRefreshAllSet.test.tsx` | 10 | PASS (all pass) |
| Backend | `test_catalog_search.py` | 0 | MISSING |
| **Total** | | **31** | |

The backend test file for T03 is well-structured with proper fixture
isolation (in-memory SQLite, dependency overrides). Tests cover the
happy path, validation errors, auth, credit guards, deduplication, and
set code normalization.

Frontend tests are thorough for both T02 (per-card refresh) and T03
(Refresh All Set), with proper mocking of hooks, API calls, and auth
state.

---

## Recommendations

1. **Remove or wire `max_age_days`** from `CatalogScanRequest`. If the
   intent was to let users control the deduplication window, replace the
   hardcoded `timedelta(hours=24)` with `timedelta(days=body.max_age_days)`.
   Otherwise, remove the field to avoid confusion.

2. **Add backend search tests** (`test_catalog_search.py`) covering
   case-insensitive matching on both name fields, at minimum 3-4 tests.
   This is low-effort and high-value for regression prevention.

3. **Create F131 diagrams** (architecture + journey `.mmd` files) per
   the project documentation rules. The architecture diagram should show
   the new `POST /catalog/scan` flow: Frontend -> API -> credit check ->
   bulk insert -> price_update_requests -> process-price-requests CLI.

4. **Consider atomicity** for the credit deduction + bulk insert flow.
   A try/except around the insert block with a compensating credit
   refund on failure would be a pragmatic improvement. Not urgent for
   this feature size but important if the pattern is reused for larger
   operations.

5. **Clarify `queued_count` semantics** -- either rename to `total_cards`
   in the response to be accurate, or change the count to reflect only
   newly inserted requests (excluding deduped ones). The current behavior
   is not wrong, just slightly misleading.

---

## Verdict

**APPROVED WITH FINDINGS.** The implementation is architecturally sound,
well-tested (31 tests), and the code quality is high. The five findings
are low-to-medium severity and none are blocking. Recommendations 1-3
should be addressed before the feature is marked as shipped; 4-5 can be
deferred to a follow-up.

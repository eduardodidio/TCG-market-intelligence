# F50 Manual Price Entry -- Tech Lead Review

**Reviewer:** TechLead Agent
**Date:** 2026-08-22
**Feature:** F50 Manual Price Entry
**Tasks reviewed:** F50-T01, F50-T02, F50-T03, F50-T04

---

## T01 -- Manual Price Backend

### Architecture
- Good reuse of `PriceObservationRow` with `source="manual"` -- no new table needed.
- Upsert uses SQLite `INSERT ON CONFLICT DO UPDATE` on the existing `(source, external_id, observed_at)` unique constraint, which is correct.
- Auto-creation of `CardRow` for unlinked entries is a sound design choice -- it avoids forcing the user to canonize before setting a price.
- IDOR protection is correct: separate 404 for not-found and 403 for wrong user.
- Currency conversion for USD input correctly uses `converter.get_display_rate()` with 422 fallback when rate unavailable.

### B1 -- BLOCKING: external_id mismatch between write and read

`upsert_manual_price` (repository.py:203) stores the observation with:
```python
external_id = f"manual_{entry_id}"
```

But `get_latest_prices_batch` (repository.py:459) queries for:
```python
manual_external_id = f"manual_{card_id}"
```

`entry_id` (collection entry PK) and `card_id` (canonical card PK) are **different values**. This means:
- A manual price is written successfully.
- But `get_latest_prices_batch` will never find it because it looks for `manual_{card_id}` while the row has `manual_{entry_id}`.
- The manual price will appear to be saved but will not show up in any collection response.

**Fix:** Use a consistent key. Since multiple collection entries can share the same `card_id`, the most correct approach is to use `card_id` in both places. The `upsert_manual_price` method should accept `card_id` instead of (or in addition to) `entry_id`, or the endpoint should resolve `card_id` from the entry and pass it. Alternatively, use `entry_id` everywhere, but then `get_latest_prices_batch` needs a way to map `card_id -> entry_id`.

**Note:** The test in `test_repository_price_source.py` uses `f"manual_{card_id}"` in the manual observation fixtures, which matches the lookup side. The test in `test_repository_manual_price.py` uses `f"manual_{entry_id}"` which matches the write side. These tests pass in isolation but do not exercise the full round-trip, masking the bug.

### Code quality
- Clean separation between endpoint handler and `_build_collection_detail` helper.
- Good structured logging with `log.info("manual_price_set", ...)`.

### Test coverage
- 5 unit tests for `upsert_manual_price` (create, external_id format, same-day upsert, multi-day, auto-create card).
- 9 schema validation tests.
- 13 API integration tests covering auth, IDOR, validation, happy path, USD conversion, PILA, exchange rate failure, auto-create card.
- **Missing:** No test exercises the full round-trip (write via `upsert_manual_price` then read via `get_latest_prices_batch`). This would have caught B1.

### Security
- Auth: `require_auth_or_api_key` dependency enforced.
- IDOR: Correct 403 for cross-user access.
- Input validation: price > 0, price <= 99999.99, currency in {BRL, USD, PILA}.
- No SQL injection risk (parameterized queries via SQLAlchemy).

---

## T02 -- Price Source Indicator

### Architecture
- `price_source` field added to `CollectionCard` and `CollectionCardDetail` schemas -- correct inheritance.
- `get_latest_prices_batch` modified to include manual price candidates with priority logic: latest date wins, manual wins same-day ties.
- The sort key `(observed_at, 1 if source == "manual" else 0)` with `reverse=True` is correct for the priority semantics.

### B2 -- IMPORTANT: N+1 query pattern in get_latest_prices_batch

The method iterates over `card_ids`, and for each card_id:
1. Queries all `SourceCardRow` for that card_id.
2. For each source card, queries `PriceObservationRow` (latest by date).
3. Queries manual price observation.

For a collection of 349 cards, this is at minimum 349 * 2 = 698 queries per list request. This was an existing pattern that was made slightly worse by adding the manual price query (+349 queries). While not introduced by F50, the modification added to the N+1 cost.

**Recommendation:** Flag for follow-up optimization -- batch the manual price lookup alongside the existing queries.

### Code quality
- Priority logic is clear and documented in the docstring.

### Test coverage
- 7 unit tests with real SQLite DB: manual wins same day, latest date wins, manual-only, myp-only, no observations, jsonld_snapshot, manual vs jsonld.
- 6 API schema tests for price_source in detail and list responses.
- 7 API integration tests for price_source propagation.
- Coverage is thorough for the priority logic.

---

## T03 -- Frontend UI

### Architecture
- `PriceSourceBadge` is a clean presentational component -- renders only for `source="manual"`, returns null otherwise.
- `ManualPriceInput` manages local state well (value, saving, error, success).
- Integration into `CollectionCardDetail` is clean -- badge next to price, input below.
- Pencil icon on `MyCollection` list is a good UX touch for quick visual identification.

### I1 -- IMPORTANT: Display currency not passed as query param

`setManualPrice` in `collection.ts` sends the request body `{ price, currency }` but does not forward the display currency as a query parameter to the endpoint. The endpoint's `currency` query param (which controls the response display currency) defaults to `BRL`. This means:

- If the user has selected USD as their display currency, after saving a manual price, the response will return the price in BRL.
- The `onSaved` callback triggers a `refetch`, which presumably uses the correct currency, so the page will update correctly.
- However, there is a brief moment where the returned data is in BRL regardless of the user's currency preference.

**Severity:** IMPORTANT -- the workaround (refetch) masks the issue, but the API response is technically incorrect for non-BRL users.

### M1 -- MINOR: Input field allows scientific notation

The `<input type="number">` HTML element accepts values like `1e5` which `parseFloat` converts to 100000, exceeding the max. The frontend validation catches this (> 99999.99), but the UX is suboptimal. Consider adding `pattern="[0-9]*\.?[0-9]*"` or using a text input with manual numeric validation.

### Code quality
- Good use of i18n throughout -- all visible strings go through `t()`.
- Success state auto-clears after 3 seconds.
- Error clears on new input.
- Save button disabled when empty or saving.
- Enter key triggers save.

### Test coverage
- 8 tests for `PriceSourceBadge` (manual shown, other sources hidden, null, undefined, tooltip, SVG, i18n).
- 12 tests for `ManualPriceInput` (render, label, disabled, negative/zero/max validation, API call, onSaved callback, success message, error message, error clear, i18n).
- 3 tests for collection API client.
- Good coverage of edge cases and user interactions.

---

## T04 -- i18n Keys

### Architecture
- 10 keys added to both `en.json` and `pt-BR.json` under the `price` namespace.
- Keys: `manual`, `manualTooltip`, `setPrice`, `enterPrice`, `save`, `saved`, `invalidPrice`, `source.manual`, `source.myp`, `source.auto`.

### Test coverage
- 22 tests: 10 per locale (key existence + non-empty string) + parity check + differentiation check.
- The parity test ensures every EN key has a PT-BR equivalent.
- The differentiation test ensures translations are not just copies.

### Code quality
- All keys follow the existing flat-nested convention.

---

## Cross-Task Consistency

### Contract alignment
- Frontend `CollectionCard.price_source?: string | null` matches backend `price_source: str | None`.
- `ManualPriceRequest` body schema (`{ price: float, currency: str }`) matches what the frontend sends.
- i18n keys used in components match the keys defined in locale files.

### Route ordering
- `PATCH /{entry_id}/price` is defined before `GET /{entry_id}` in the router, which is fine -- FastAPI matches by method, not order, for parameterized routes.

---

## Documentation

### D1 -- IMPORTANT: Missing diagrams
Per `CLAUDE.md`, every feature must produce or update at least two Mermaid diagrams:
1. Architecture diagram (`F50-architecture.mmd`)
2. User journey diagram (`F50-journey.mmd`)

Neither exists under `docs/diagrams/`.

### D2 -- IMPORTANT: Missing README update
Per `CLAUDE.md`, every shipped feature must update the project `README.md`. No mention of F50 or manual price entry found.

---

## Verdict: REJECTED

### Blocking issues
1. **B1:** `external_id` mismatch between `upsert_manual_price` (uses `entry_id`) and `get_latest_prices_batch` (looks up by `card_id`). Manual prices are written but never read back. This is a data correctness bug that makes the entire feature non-functional in production.

### Important issues (must fix or create follow-up)
2. **I1:** Display currency not forwarded as query param in `setManualPrice` API call.
3. **D1:** Missing Mermaid diagrams (F50-architecture.mmd, F50-journey.mmd).
4. **D2:** Missing README.md update.
5. **B2:** N+1 query pattern in `get_latest_prices_batch` (existing, worsened -- follow-up OK).

### Minor issues
6. **M1:** Number input accepts scientific notation.

---

## Retrospective Seeds

- **Pattern:** Write-side and read-side use different key formats for the same logical entity (`manual_{entry_id}` vs `manual_{card_id}`).
- **Role(s) affected:** developer, techlead
- **Lesson:** When a feature stores data with a computed key (like `f"manual_{x}"`), always verify that all read paths use the same key derivation. Add at least one round-trip integration test that writes via the API endpoint and reads back via the list/detail endpoint to catch key mismatches.

- **Pattern:** Test fixtures for related code paths use hardcoded values that happen to match the expected format but do not exercise the actual key derivation logic.
- **Role(s) affected:** developer
- **Lesson:** Integration tests should exercise the full data path (write then read) rather than testing write and read in isolation with independently constructed fixture data. The two test files used `manual_{entry_id}` and `manual_{card_id}` respectively, each passing in isolation but hiding the mismatch.

- **Pattern:** Missing documentation deliverables (diagrams, README).
- **Role(s) affected:** developer
- **Lesson:** Check the CLAUDE.md documentation requirements checklist before marking a feature as complete. This has been flagged in multiple prior features (F15, P2).

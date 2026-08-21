# F15 Test Plan

## 1. Scope

**In scope:**
- T01: MYP-to-Scryfall set code mapping utility (frontend + backend)
- T02: Image URL generation with mapped set codes + fallback chain (frontend + backend)
- T03: BRL currency indicator in sidebar (frontend only)
- T04: Collection card detail page, API endpoint, and repository method (frontend + backend)

**Out of scope:**
- Scryfall API availability (all image URLs are constructed locally, never fetched in tests)
- CSV import logic (set codes arrive already stored in DB)
- Existing CardDetail page for Explore cards (no changes)
- Price formatting (`formatBRL` is unchanged)
- E2E/browser tests (no Playwright/Cypress in this project)

## 2. Test Strategy

| Layer | Tool | Rationale |
|-------|------|-----------|
| Backend unit | pytest | Pure functions (set code mapping, URL builder) and isolated repo methods |
| Backend integration | pytest + TestClient | FastAPI endpoint for collection detail (`GET /collection/{id}`) |
| Frontend unit | Vitest | Set code mapping utility, scryfall URL helpers |
| Frontend component | Vitest + RTL | CollectionCardTile image fallback, Layout currency badge, CollectionCardDetail rendering |

No E2E tests. The fixes are display-level with clear unit boundaries. Component tests with React Testing Library provide sufficient confidence for rendering behavior.

## 3. Test Matrix

### T01 -- Set Code Mapping Utility

| ID | Description | Type | Priority |
|----|-------------|------|----------|
| T01-01 | Borderless prefix `bl` maps correctly (bldmr->dmr, bl2x2->2x2, blfdn->fdn) | unit | P0 |
| T01-02 | Extended art prefix `ex` maps correctly (exdmu->dmu) | unit | P0 |
| T01-03 | Extended art prefix `ea` maps correctly (eafic->fic, eahoc->hoc) | unit | P0 |
| T01-04 | Showcase prefix `sr`/`sk` maps correctly (srltr->ltr, skmh2->mh2) | unit | P0 |
| T01-05 | Secret Lair `sld*` with numeric suffix maps to `sld` (sld158->sld) | unit | P0 |
| T01-06 | Other prefixes: `fe`, `sm`, `cb`, `bb`, `dh`, `gf`, `pl`, `vv` | unit | P1 |
| T01-07 | Standard set codes pass through unchanged (dmr, dmu, ltr, 2x2) | unit | P0 |
| T01-08 | Unknown/unrecognized codes return input unchanged | unit | P0 |
| T01-09 | Case-insensitive handling (BLDMR, BLdmr) | unit | P1 |
| T01-10 | Empty string and edge cases do not throw | unit | P1 |
| T01-11 | Backend and frontend produce identical results for all known codes | unit | P0 |

### T02 -- Image URL Fixes

| ID | Description | Type | Priority |
|----|-------------|------|----------|
| T02-01 | Backend `_scryfall_image_url("bldmr", "437")` returns URL containing `/dmr/` | unit | P0 |
| T02-02 | Backend `_scryfall_image_url("exdmu", "410")` returns URL containing `/dmu/` | unit | P0 |
| T02-03 | Backend `_scryfall_image_url("sld158", "1245")` returns URL containing `/sld/` | unit | P0 |
| T02-04 | Backend `_scryfall_image_url("dmr", "100")` passes through unchanged | unit | P0 |
| T02-05 | Collection list API response contains mapped `image_url` for variant cards | integration | P0 |
| T02-06 | Frontend `CollectionCardTile` renders img with backend-provided mapped URL | component | P0 |
| T02-07 | Frontend fallback: name-based URL used on primary image error | component | P1 |
| T02-08 | Frontend fallback: placeholder SVG shown when both image sources fail | component | P1 |
| T02-09 | No regression: standard set code images on Explore page unaffected | component | P1 |

### T03 -- BRL Currency Indicator

| ID | Description | Type | Priority |
|----|-------------|------|----------|
| T03-01 | Layout renders "BRL" text in sidebar | component | P0 |
| T03-02 | Layout renders element with `aria-label="Brazilian flag"` | component | P0 |
| T03-03 | Flag element has `role="img"` for accessibility | component | P1 |
| T03-04 | Currency indicator present on initial render (no interaction needed) | component | P1 |

### T04 -- Collection Card Detail

| ID | Description | Type | Priority |
|----|-------------|------|----------|
| T04-01 | Backend: `GET /collection/{id}` returns 200 with full entry data | integration | P0 |
| T04-02 | Backend: `GET /collection/{id}` returns 404 for non-existent entry | integration | P0 |
| T04-03 | Backend: linked entry response includes price history and source data | integration | P0 |
| T04-04 | Backend: unlinked entry response returns null for price/source fields | integration | P0 |
| T04-05 | Backend: `CollectionCardDetail` schema validates all required fields | unit | P1 |
| T04-06 | Backend: repository `get_collection_entry` returns correct row | unit | P0 |
| T04-07 | Backend: repository `get_collection_entry` returns None for missing ID | unit | P1 |
| T04-08 | Frontend: renders card name (EN + PT), set code, collector number | component | P0 |
| T04-09 | Frontend: renders collection metadata badges (quantity, quality, language, extras) | component | P0 |
| T04-10 | Frontend: renders quantity badge only when quantity > 1 | component | P1 |
| T04-11 | Frontend: renders price chart section for linked cards | component | P0 |
| T04-12 | Frontend: renders "Not linked" state for unlinked cards | component | P0 |
| T04-13 | Frontend: breadcrumb links back to `/collection` | component | P1 |
| T04-14 | Frontend: external links (Scryfall, LigaMagic) present and correctly built | component | P1 |
| T04-15 | Frontend: card image uses mapped Scryfall URL | component | P1 |
| T04-16 | MyCollection: all card tiles link to `/collection/{id}` not `/cards/` | component | P0 |
| T04-17 | MyCollection: no unlinked-card fallback to Explore page remains | component | P0 |

## 4. Test Files

### T01

| File (new) | Purpose |
|------------|---------|
| `tests/utils/test_set_code_map.py` | Backend mapping: all known codes, pass-through, edge cases (T01-01 through T01-10) |
| `frontend/src/utils/__tests__/setCodeMap.test.ts` | Frontend mapping: mirror of backend tests (T01-01 through T01-10) |

### T02

| File | Purpose |
|------|---------|
| `tests/api/test_collection_router.py` (new or extend existing) | `_scryfall_image_url` with mapped codes (T02-01 through T02-05) |
| `frontend/src/pages/__tests__/MyCollection.test.tsx` (new or extend) | Image rendering and fallback chain (T02-06 through T02-09) |

### T03

| File | Purpose |
|------|---------|
| `frontend/tests/components/Layout.test.tsx` (modify) | Add tests for BRL badge (T03-01 through T03-04) |

### T04

| File | Purpose |
|------|---------|
| `tests/api/test_collection_router.py` (extend) | New detail endpoint (T04-01 through T04-07) |
| `frontend/src/pages/__tests__/CollectionCardDetail.test.tsx` (new) | Detail page rendering (T04-08 through T04-15) |
| `frontend/src/pages/__tests__/MyCollection.test.tsx` (modify) | Link targets updated (T04-16, T04-17) |

**Estimated new test count:** ~45 backend, ~30 frontend (~75 total).

## 5. Fixtures & Mocks

### Backend

| Fixture | Used by | Description |
|---------|---------|-------------|
| `VARIANT_CODE_PAIRS` | T01 tests | List of `(myp_code, expected_scryfall_code)` tuples covering all ~40 known variants |
| `PASSTHROUGH_CODES` | T01 tests | List of standard codes that should not be modified |
| `linked_collection_entry` | T02, T04 | `UserCollectionRow` with `card_id` set, quantity=2, quality="NM", language="EN" |
| `unlinked_collection_entry` | T04 | `UserCollectionRow` with `card_id=None` |
| `mock_repository` | T04 | Repository mock with `get_collection_entry` returning fixture entries |
| `test_client` | T02, T04 | FastAPI `TestClient` with in-memory SQLite (existing pattern from `test_collection_sync.py`) |

### Frontend

| Mock / Fixture | Used by | Description |
|----------------|---------|-------------|
| `linkedCollectionCard` | T02, T04 | Collection card object with `card_id`, `image_url`, variant set code |
| `unlinkedCollectionCard` | T04 | Collection card object with `card_id: null` |
| `mockFetchCollectionEntry` | T04 | MSW handler or vi.fn mock for `GET /api/v1/collection/:id` |
| `renderWithRouter` | T04 | Helper wrapping component in `MemoryRouter` with route params |
| `vi.fn` for `img.onError` | T02 | Simulate image load failure to test fallback chain |

## 6. Coverage Targets

| Area | Current | Expected after F15 |
|------|---------|-------------------|
| Backend overall | 91.80% | >= 91% (net neutral -- new code fully tested) |
| `src/utils/set_code_map.py` | N/A (new) | 100% |
| `src/api/routers/collection.py` | existing | >= 90% (new endpoint + image URL fix covered) |
| `src/database/repository.py` | existing | >= 90% (new `get_collection_entry` covered) |
| Frontend overall | 192 tests | ~220+ tests |
| `frontend/src/utils/setCodeMap.ts` | N/A (new) | 100% |

Coverage must not drop below `--cov-fail-under=70` (pyproject.toml threshold). Given the current 91.80% baseline and fully-tested new code, no risk here.

## 7. Risks & Gaps

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Incomplete variant code coverage** | Some MYP codes not in the static map produce wrong Scryfall URLs | Heuristic prefix-stripping as fallback; name-based image fallback as safety net. T01-08 validates graceful passthrough. |
| **Scryfall collector number mismatch** | Variant printings may have different collector numbers than base set | Out of scope for F15 -- the name-based fallback (T02-07) handles this. Document as known limitation. |
| **No visual regression testing** | CSS/layout issues in currency badge or detail page not caught | RTL tests verify DOM structure and accessibility attributes, not pixel output. Manual spot-check recommended during QA. |
| **`_scryfall_image_url` is a private function** | Testing it directly is fragile if internals change | Test through the API response (`image_url` field in collection list endpoint) for integration coverage. Unit test the mapping function separately. |
| **Route wiring** | New `/collection/:id` route could break existing navigation | T04-16/T04-17 verify link targets in MyCollection. Manual navigation test during QA. |
| **Existing Layout tests** | Modifying `Layout.test.tsx` could break if test file has tight assertions | Read existing test file before adding T03 tests; use additive assertions only. |

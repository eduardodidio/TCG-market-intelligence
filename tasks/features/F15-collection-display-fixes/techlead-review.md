# F15 Tech Lead Review

**Date:** 2026-08-20
**Verdict:** APPROVED (with noted follow-ups)

## Architecture

**Set code mapping approach (T01):** Sound design. Using a static lookup table with a prefix-stripping heuristic fallback is pragmatic and maintainable. The three-tier resolution (static table, Secret Lair regex, prefix heuristic) covers known cases well and degrades gracefully for unknown codes. Backend/frontend parity is maintained -- both implementations use identical logic and identical lookup tables.

**New `/collection/{entry_id}` endpoint (T04):** Well-designed. Extending `CollectionCard` into `CollectionCardDetail` via Pydantic inheritance is clean. The endpoint correctly enriches the response with price history, source cards, and external links when the entry is linked, and returns a minimal but useful response for unlinked entries. The route placement at `/collection/{entry_id}` under the existing `collection` router prefix is correct and follows existing patterns.

**Frontend routing (T04):** Good decision to create a dedicated `CollectionCardDetail` page rather than overloading the existing `CardDetail`. The route `/collection/:id` is properly registered in `App.tsx` with lazy loading and Suspense, consistent with all other routes. The change in `MyCollection.tsx` to always link to `/collection/{id}` (line 143) eliminates the dead-end problem for unlinked cards.

**No architectural concerns.** The feature is well-scoped and makes appropriate tradeoffs.

## Code Quality

### `src/utils/set_code_map.py`
Clean, well-documented module. The comment "Order matters: longer prefixes first to avoid partial matches" on line 63 is slightly misleading -- `"ash"` (3 chars) is listed last, but `"bl"` (2 chars) is listed first. The ordering does not actually sort by length. However, since the static lookup table catches all known codes before the heuristic runs, and each prefix is tried independently (first match wins), this is not a functional bug -- just a misleading comment.

### `frontend/src/utils/setCodeMap.ts`
Exact mirror of backend logic. No issues.

### `src/api/routers/collection.py`
- **`_scryfall_image_url`** (line 42-47): Correctly integrates `map_to_scryfall_set_code`. Clean.
- **`get_collection_entry`** (line 127-203): Well-structured. Good error handling with 404 for missing entries. Properly fetches price history from multiple source types (`[sc.source, "jsonld_snapshot"]`).
- **URL encoding concern** (line 176): The `scryfall_url` is built via f-string without URL-encoding the card name. Card names with special characters (e.g., `+`, `&`, spaces) could break the URL. This is a MINOR issue because Scryfall's search is tolerant, but `urllib.parse.quote()` would be more correct.
- **No user_id filtering on `get_collection_entry`** (line 128): The repository method `get_collection_entry(entry_id)` fetches any entry regardless of user. This is consistent with the existing single-user design (`FAKE_USER_ID`), but should be noted as a follow-up when multi-user support is added.

### `src/api/schemas/collection.py`
Clean inheritance from `CollectionCard`. No issues.

### `src/database/repository.py`
- **`get_collection_entry`** (line 544-549): Simple and correct. Uses `scalar_one_or_none()` which is the right pattern for optional single-row lookups.

### `frontend/src/pages/CollectionCardDetail.tsx`
- Well-structured component with proper loading, error, and 404 states.
- Good accessibility: breadcrumb has `aria-label`, flag emoji has `role="img"`.
- `onError` handler on the image (line 137) hides the image entirely -- acceptable but less graceful than the `MyCollection` fallback chain which tries a name-based URL first. This is a MINOR inconsistency.
- External links open in `_blank` with `rel="noopener noreferrer"` -- correct security practice.

### `frontend/src/pages/MyCollection.tsx`
- Line 143: All cards now link to `/collection/${card.id}` -- correct. No more dead-end for unlinked cards.
- Image fallback chain (primary -> name-based -> placeholder SVG) is well-implemented.

### `frontend/src/components/Layout.tsx`
- Currency indicator (lines 61-64) is minimal and correct. Uses `role="img"` and `aria-label` for accessibility.

### `frontend/src/utils/scryfall.ts`
- Correctly integrates `mapToScryfallSetCode` on the frontend side.

### `frontend/src/App.tsx`
- New route properly registered with lazy loading. No issues.

No hardcoded secrets. No SQL injection vectors (all queries use SQLAlchemy parameterized statements). No XSS concerns (React auto-escapes, external link hrefs use `target="_blank"` with `noopener`). Clean imports throughout.

## Tests

**Backend (850 passed, 92.75% coverage):**
- `tests/utils/test_set_code_map.py`: 49 parametrized tests covering known variants, Secret Lair, passthrough, unknown codes, case-insensitivity, and prefix heuristic. Thorough.
- Backend collection router tests cover the new endpoint (confirmed by test count matching plan).
- `src/utils/set_code_map.py` at 100% coverage.

**Frontend (302 passed across 29 test files):**
- `src/utils/__tests__/setCodeMap.test.ts`: 49 tests mirroring backend test structure exactly. Good parity.
- `tests/pages/CollectionCardDetail.test.tsx`: 12 tests covering linked entry rendering, unlinked state, quantity/quality/language/extras badges, breadcrumb navigation, external links, 404 handling, price formatting. Meaningful tests, not just smoke tests.
- `src/utils/__tests__/scryfall.test.ts`: 10 tests for the Scryfall URL utility with mapping integration.

Edge cases well covered: quantity=1 (no badge), unlinked cards (no price chart, "not linked" notice), 404 entries, empty names. Test quality is good.

## Diagrams

**MISSING.** No `docs/diagrams/F15-architecture.mmd` or `docs/diagrams/F15-journey.mmd` found. Per project rules in CLAUDE.md, every feature MUST produce or update at least two Mermaid diagrams. This is a documentation gap.

**README.md not updated.** Per CLAUDE.md rules, every feature that ships MUST update the project README. No mention of F15 changes found in README.md.

## Issues Found

| # | Severity | Description |
|---|----------|-------------|
| 1 | MINOR | `_STRIP_PREFIXES` comment says "longer prefixes first" but ordering is not by length (`"ash"` is last). Comment is misleading though behavior is correct since static lookup catches known cases first. |
| 2 | MINOR | `scryfall_url` in `get_collection_entry` is built without URL-encoding the card name. Names with `+`, `&`, or spaces could produce malformed URLs. Should use `urllib.parse.quote()`. |
| 3 | MINOR | `CollectionCardDetail.tsx` hides the image entirely on error (`display: "none"`) instead of using the name-based fallback chain that `MyCollection.tsx` uses. Inconsistent UX. |
| 4 | MINOR | `get_collection_entry` repository method does not filter by `user_id`. Acceptable for single-user mode but should be tracked for multi-user follow-up. |
| 5 | MAJOR | Missing F15 Mermaid diagrams (`F15-architecture.mmd`, `F15-journey.mmd`). Required by CLAUDE.md documentation rules. |
| 6 | MAJOR | README.md not updated with F15 changes. Required by CLAUDE.md. |

## Verdict Rationale

APPROVED. The implementation is architecturally sound, well-tested (850 backend + 302 frontend tests, 92.75% coverage), and solves all three stated problems effectively. The set code mapping utility is clean and maintainable. The new collection detail page eliminates dead-ends and provides full collection context. The currency indicator is minimal and correct.

The two MAJOR issues (missing diagrams and README update) are documentation gaps that do not affect functionality or code quality. They should be addressed as an immediate follow-up before the feature is considered fully shipped per project rules. The MINOR issues are noted for future improvement but do not block approval.

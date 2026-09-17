# F133 QA Report -- Deck Builder & Evaluator

**Date:** 2026-09-17
**Validator:** QA (automated)
**Verdict:** PASS

---

## Test Results

### Backend Unit Tests

| Test Suite | Tests | Status |
|------------|-------|--------|
| `tests/unit/decks/test_evaluator.py` | 35 | All pass |
| `tests/unit/decks/test_builder.py` | 19 | All pass |
| `tests/unit/decks/test_suggestions.py` | 29 | All pass |
| `tests/unit/api/test_deck_endpoints.py` | 27 | All pass |
| Pre-existing deck tests (parser, valuation, importer) | 94 | All pass |
| **Total backend (decks/ + API)** | **177 + 27 = 204** | **All pass** |

### Frontend Tests

| Test Suite | Tests | Status |
|------------|-------|--------|
| `DeckEvaluationPanel.test.tsx` | 11 | All pass |
| `DeckBuildWizard.test.tsx` | 12 | All pass |
| `Layout.test.tsx` (F133 nav subset) | 10 | All pass |
| `Layout.test.tsx` (all) | 36 | All pass |
| **Total frontend (F133-specific)** | **59** | **All pass** |

### Build & Lint

| Check | Status |
|-------|--------|
| `ruff check src/decks/` | All checks passed |
| `npm run build` (frontend) | Built in 3.75s, 0 errors |
| TypeScript compilation | Pass (part of build) |

---

## Coverage Analysis

### Backend Coverage (F133 modules only)

| Module | Stmts | Covered | Coverage |
|--------|-------|---------|----------|
| `src/decks/evaluator.py` | 200 | 185 | 92% |
| `src/decks/builder.py` | 197 | 158 | 80% |
| `src/decks/suggestions.py` | 99 | 99 | 100% |
| `src/domain/models.py` | 445 | 440 | 99% |

Uncovered lines in `builder.py` are primarily the `get_commander_candidates`
function (tested via API-level mocking in `test_deck_endpoints.py`) and
some Session-dependent query paths that require integration-level testing.

### Frontend Test Coverage (qualitative)

- **DeckEvaluationPanel:** loading, error, mana curve, type dist, color
  dist, legality (legal + illegal), budget (total + expensive), suggestions,
  format selector, composition stats = comprehensive.
- **DeckBuildWizard:** all 4 steps tested, format selection, commander
  search, color picker, archetype/budget, generate API call, save
  navigation, regenerate, back navigation, error display, budget presets.
- **Layout:** both new nav items verified present in beta section, correct
  href, correct label key, correct icon, correct ordering, tooltip in
  collapsed mode.

---

## Validation Checklist

### Functional Requirements

| Requirement | Validated | Notes |
|-------------|-----------|-------|
| Evaluator is pure (no DB) | Yes | Only imports `re`, `collections`, `decimal`, `domain.models` |
| Builder uses Repository | Yes | `Session(repo.engine)` for catalog queries |
| Suggestions separate module | Yes | `src/decks/suggestions.py` with own templates |
| Mana curve analysis | Yes | CMC bucketed 0-7+, lands excluded, quantity-weighted |
| Color distribution | Yes | Pip-based counting, hybrid handling |
| Type distribution | Yes | Priority-ordered classification |
| Legality check | Yes | Format-specific, singleton, basic land exemption |
| Budget analysis | Yes | Price tiers, top 5 expensive, total value |
| Suggestions severity sort | Yes | critical -> warnings -> info |
| Commander format support | Yes | 100-card singleton, commander slot, staples |
| 60-card format scaling | Yes | Proportional scaling from 100-card templates |
| Wizard 4-step flow | Yes | Format -> Colors/Commander -> Archetype/Budget -> Review |
| Commander search debounce | Yes | 300ms debounce, min 2 chars |
| Auto-color from commander | Yes | Extracts from `color_identity` string |
| Deck auto-save on generate | Yes | Creates DeckRow + DeckCardRows |
| Evaluation tab on DeckView | Yes | Tab switcher with URL param persistence |
| Nav items in Beta section | Yes | Build Deck + Deck Evaluator |
| API auth on all endpoints | Yes | `require_auth_or_api_key` dependency |

### API Endpoint Verification

| Endpoint | Method | Auth | Tested | Notes |
|----------|--------|------|--------|-------|
| `/decks/{id}/evaluate` | GET | Yes | Yes | Format/archetype as query params |
| `/decks/generate` | POST | Yes | Yes | Validates format + commander |
| `/decks/commanders` | GET | Yes | Yes | Color filter + search |

### Routing Verification

| Route | Backend | Frontend | Notes |
|-------|---------|----------|-------|
| `/commanders` before `/{deck_id}` | Yes (line 238 vs 625) | N/A | Correct FastAPI ordering |
| `/generate` before `/{deck_id}` | Yes (line 263 vs 625) | N/A | Correct FastAPI ordering |
| `/decks/build` before `/decks/:id` | N/A | Yes (line 345 vs 359) | Correct React Router ordering |

### Regression Check

| Area | Status | Notes |
|------|--------|-------|
| Existing deck import | Pass | 4 tests pass |
| Existing deck list | Pass | 2 tests pass |
| Existing deck detail | Pass | 3 tests pass |
| Existing deck delete | Pass | 2 tests pass |
| Existing deck ranking | Untouched | No changes to ranking logic |
| Existing deck valuation | Pass | 3 tests pass |
| Layout sidebar tests | Pass | 36 tests, all existing + 10 new |

---

## Issues Found

None blocking.

### Advisory Issues (not blocking)

1. **N+1 query in evaluate endpoint** (line 507-510 of `decks.py`):
   `get_card_by_id` called per card. For 100-card decks this means ~100
   queries. Functionally correct, perf acceptable for user-initiated action.

2. **Budget input validation**: `parseFloat("abc")` produces `NaN` which
   Pydantic coerces to `null`. No crash, but could show validation message
   in UI.

3. **`/decks/evaluate` redirect**: Route redirects to `/decks?evaluate=true`
   but the DeckList page does not appear to consume the `evaluate` query
   param. The nav item works as a conceptual pointer to "go to decks and
   try evaluation," but the parameter is unused. The actual evaluation lives
   on individual deck pages via the tab.

---

## Test Gap Analysis

| Gap | Severity | Notes |
|-----|----------|-------|
| Integration test with real DB (builder) | Low | Builder tested via mock Session, adequate |
| Commander search with colors filter | Low | Tested at API level (mock), not integration |
| DeckView tab URL param initialization | Low | Covered by DeckView existing tests |
| Dark mode styling on new components | Info | Visual, not functional |

---

## Conclusion

F133 is well-implemented across all 6 tasks and 3 waves. The separation of
concerns between evaluator (pure), builder (repository), and suggestions
(template-based) is clean. Test coverage is strong: 204 backend tests and
59 frontend tests with 0 failures. The frontend build succeeds, linting
passes, no regressions detected. All three advisory findings are non-blocking
optimizations.

**Final verdict: PASS -- ready for merge to homol.**

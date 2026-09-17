# F133 Tech Lead Review -- Deck Builder & Evaluator

**Date:** 2026-09-17
**Reviewer:** Tech Lead (automated)
**Verdict:** APPROVED

---

## Summary

Feature F133 delivers a deck builder wizard and deck evaluation panel across
6 tasks in 3 waves. The implementation is architecturally clean, well-tested,
and follows existing project patterns. The evaluator is correctly kept as a
pure function layer (no DB imports), the builder uses Repository through
explicit SQLAlchemy Sessions, and the suggestion engine is properly separated
into its own module. Frontend components follow established patterns with
Recharts, i18n, and data-testid conventions.

---

## Wave 0 -- Backend Services

### T01: Deck Evaluator (`src/decks/evaluator.py`)

**Architecture: PASS**
- Pure module -- imports only `re`, `collections`, `decimal`, and the domain
  model `DeckEvaluation`. No database, no repository, no side effects.
- All functions accept plain dicts, making them trivially testable.
- `parse_cmc` handles edge cases well: X costs, hybrid, phyrexian, split/DFC
  cards (front-face-only), colorless pips.
- `classify_card_type` uses priority ordering (Land > Creature > Planeswalker
  > ...), which matches MTG convention.
- Budget analysis categorizes price tiers correctly (budget < 5, mid 5-20,
  premium 20-50, chase 50+).
- Legality check handles singleton violations, basic land exemptions, and
  card count validation per format.

**Minor finding:** The `evaluate_deck` function performs a late import of
`src.decks.suggestions.generate_suggestions` at line 439. This is intentional
to break a circular dependency (suggestions imports `DeckEvaluation` from
domain), but it means the import happens on every call. This is functionally
correct and the cost is negligible for this use case.

### T02: Deck Builder (`src/decks/builder.py`)

**Architecture: PASS**
- Uses SQLAlchemy `Session` directly (not the Repository abstraction) for
  complex queries. This is acceptable since the builder needs fine-grained
  control over joins and ordering.
- Archetype templates sum correctly to 100 cards for commander. The
  `_get_target_composition` function scales proportionally for 60-card
  formats with land as remainder.
- Color identity matching is done post-query (Python-side) rather than in
  SQL -- documented as "safer than SQL for parsed strings." This is correct
  given that `color_identity` is a concatenated string like "WUB".
- Commander staple auto-inclusion (Command Tower, Sol Ring, Arcane Signet)
  correctly adjusts composition counts.
- Budget enforcement in `_select_cards` properly skips cards that exceed
  remaining budget.

**Finding (advisory, not blocking):** Line 507, `card_info` is built with
N+1 `get_card_by_id` calls in the evaluate endpoint. For a 100-card
commander deck, this means ~100 individual DB queries. A batch fetch method
(`get_cards_by_ids_batch`) would be more efficient. Not a blocker since
deck evaluation is not a hot path (user-initiated, once per view).

---

## Wave 1 -- Endpoints + Frontend

### T03: Evaluate Endpoint + DeckEvaluationPanel

**API Design: PASS**
- `GET /decks/{deck_id}/evaluate?format=commander&archetype=aggro` follows
  REST conventions. Query params for optional filters.
- Proper auth check (user_id must match deck owner).
- Enriches deck cards with CardRow data before passing to pure evaluator.
- Unlinked cards (card_id=None) are counted and reported as a suggestion.
- Response schema (`DeckEvaluationResponse`) is well-structured with typed
  sub-schemas for mana curve, type distribution, color distribution,
  legality, budget, and suggestions.

**Frontend: PASS**
- `DeckEvaluationPanel` uses BarChart for mana curve, PieChart for type and
  color distributions -- consistent with existing Recharts usage.
- Format selector triggers re-fetch via `useCallback` + `useEffect`.
- Loading, error, and empty states all handled.
- All sections have `data-testid` attributes for testability.
- i18n keys use `defaultValue` fallback pattern consistently.

### T04: Generate Endpoint + DeckBuildWizard

**API Design: PASS**
- `POST /decks/generate` validates format against `_VALID_FORMATS` set.
- Commander validation checks card exists AND is Legendary Creature.
- Auto-saves generated deck (creates DeckRow + DeckCardRows) and returns
  the deck_id for immediate navigation.
- Auto-generates deck name: `{colors} {Archetype} -- {date}` with optional
  user override.
- `generateDeck` API call has 30s timeout (`timeoutMs: 30_000`), appropriate
  for catalog queries.

**Frontend: PASS**
- 4-step wizard with clear progress indicator.
- Step 1: Format selection (6 formats) with card descriptions.
- Step 2: Commander search (debounced, 300ms) or color picker, context-
  dependent on format.
- Step 3: Archetype + budget (with R$100/500/1000 presets) + "prioritize
  owned" checkbox.
- Step 4: Review with card grid, warnings, stats, regenerate button, and
  save/navigate.
- Commander auto-sets colors from color_identity.
- Proper error handling with `wizard-error` display.

---

## Wave 2 -- Suggestions + Integration

### T05: Suggestion Engine (`src/decks/suggestions.py`)

**Architecture: PASS**
- Clean separation from evaluator -- receives a `DeckEvaluation` dataclass,
  returns `list[str]`.
- `ARCHETYPE_TEMPLATES` with per-archetype ranges for land, creature,
  instant, sorcery, enchantment, artifact counts, plus CMC and minimum
  counts for removal/draw/ramp.
- Suggestions are severity-sorted: critical (card count, legality) first,
  then warnings (land/creature/CMC), then info (color balance, interaction).
- Generic fallback when no archetype template matches.
- TYPE_CHECKING import guard for `DeckEvaluation` prevents circular imports.

### T06: Navigation + Integration

**Navigation: PASS**
- Two new items in `BETA_NAV_ITEMS`: "Build Deck" (`/decks/build`) with
  wrench icon, "Deck Evaluator" (`/decks/evaluate`) with beaker icon.
- Positioned after "Top Decks" and before "Marketplace" -- logical grouping.
- `requiresAuth: true` on both -- correct.
- `/decks/evaluate` route redirects to `/decks?evaluate=true` (evaluation
  lives as a tab on DeckView, not a separate page).

**DeckView Integration: PASS**
- Tab switcher (`cards` | `evaluation`) with URL param persistence
  (`?tab=evaluation`).
- `DeckEvaluationPanel` renders in the evaluation tab, receiving `deckId`.
- Tab state initialized from URL params, maintained on switch.

---

## Schema & Model Review

- `DeckEvaluation` dataclass in `src/domain/models.py` uses appropriate
  types: `dict[int, int]` for mana curve, `set[str]` for color identity.
- `DeckBuildParams` includes all necessary builder inputs with sensible
  defaults.
- `GeneratedDeck` captures the full output including warnings.
- Pydantic schemas in `src/api/schemas/decks.py` mirror the domain models
  with proper serialization (Decimal -> float, set -> sorted list).
- Frontend TypeScript types in `api.ts` match the API response shapes.

---

## Findings

| # | Severity | Location | Description |
|---|----------|----------|-------------|
| 1 | Advisory | `decks.py:507` | N+1 card fetch in evaluate endpoint. Consider adding `get_cards_by_ids_batch()` to Repository. |
| 2 | Advisory | `evaluator.py:439` | Late import of suggestions module in `evaluate_deck()`. Documented, not a perf concern. |
| 3 | Advisory | `DeckBuildWizard.tsx:165` | `budget_limit` parsed as `parseFloat` from string. Edge case: user types "abc" -> `NaN` sent to API. Backend would treat as `null` (Pydantic coercion), but frontend could validate. |

---

## Recommendations

1. **Future optimization:** Add `get_cards_by_ids_batch(ids: list[int])` to
   Repository and use it in the evaluate endpoint to replace the N+1 loop.
   Not urgent -- decks are typically 60-100 cards and evaluation is not a
   hot path.

2. **Future enhancement:** The `archetype` parameter in the evaluate
   endpoint could be auto-detected from the deck composition (e.g., high
   creature count -> aggro, high instant count -> control). This would
   remove the need for users to manually specify archetype.

3. **i18n completeness:** The `nav.buildDeck` and `nav.deckEvaluator` keys
   should be verified in all language JSON files. The `defaultValue`
   fallback ensures no broken UI, but translations should be added.

# F188 -- Synergy-Aware Deck Generation

## Summary

The deck builder (`src/decks/builder.py`) generates decks with ZERO synergy
consideration. Cards are picked purely by color identity, archetype slot
counts, rarity ordering, budget, and ownership. There is no analysis of
the commander's abilities, no keyword matching, no tribal synergy, and no
mechanical synergy. The `oracle_text` field does not exist in `CardRow`,
so the system has no data to analyze card abilities. Additionally,
`suggestions.py` defines `removal_min`, `card_draw_min`, `ramp_min` in
archetype templates but NEVER validates them -- dead code.

This feature adds:
1. The `oracle_text` column to the card catalog (populated from Scryfall)
2. A pure synergy scoring engine (`src/decks/synergy.py`)
3. Integration of synergy scoring into the deck builder
4. Validation of role minimums in the evaluator/suggestions
5. Frontend display of synergy metrics and per-card synergy badges

## Affected Files

### Backend (modified)
- `src/database/models.py` -- add `oracle_text` to CardRow
- `src/database/repository.py` -- ALTER TABLE migration for oracle_text
- `src/catalog/scryfall.py` -- add oracle_text to CatalogCard
- `src/catalog/seeder.py` -- populate oracle_text in upsert
- `src/decks/builder.py` -- integrate synergy scoring into _query_candidates + _select_cards
- `src/decks/evaluator.py` -- add synergy metrics to evaluation output
- `src/decks/suggestions.py` -- validate role minimums using classify_card_role
- `src/domain/models.py` -- update DeckBuildParams, GeneratedDeck, DeckEvaluation
- `src/api/schemas/decks.py` -- add synergy fields to schemas
- `src/api/routers/decks.py` -- pass synergy_weight param, return synergy data
- `src/cli/main.py` -- add `catalog update-oracle` CLI command

### Backend (new)
- `src/decks/synergy.py` -- synergy scoring engine (pure functions)

### Frontend (modified)
- `frontend/src/components/DeckEvaluationPanel.tsx` -- synergy score + role breakdown display
- `frontend/src/pages/DeckBuildWizard.tsx` -- synergy badges in review step
- `frontend/src/types/api.ts` -- updated TypeScript interfaces
- `frontend/src/locales/en/translation.json` -- i18n keys for synergy UI
- `frontend/src/locales/pt/translation.json` -- i18n keys for synergy UI

### Tests (new)
- `tests/unit/decks/test_synergy.py` -- synergy engine unit tests
- `tests/unit/decks/test_builder_synergy.py` -- builder integration tests
- `tests/unit/decks/test_evaluator_synergy.py` -- evaluator synergy metric tests
- `tests/unit/decks/test_suggestions_roles.py` -- role validation tests
- `frontend/src/components/__tests__/DeckEvaluationPanel.test.tsx` -- synergy UI tests
- `frontend/src/pages/__tests__/DeckBuildWizard.synergy.test.tsx` -- synergy badge tests

### Test Impact (existing files that need updates)
- `tests/unit/decks/test_builder.py` -- _select_cards signature changes
- `tests/unit/decks/test_evaluator.py` -- DeckEvaluation gains new fields
- `tests/unit/decks/test_suggestions.py` -- generate_suggestions now validates roles

### Shared/high-conflict files
- `src/domain/models.py` -- T04 adds synergy fields to `DeckEvaluation` (~line 658), T05 adds synergy_weight to `DeckBuildParams` (~line 678). Both in Wave 1 but edit different dataclasses ~20 lines apart (clean 3-way merge). T01 (Wave 0) does NOT touch this file -- oracle_text flows through CardRow/CatalogCard only.
- `src/api/schemas/decks.py` -- T05 adds synergy_weight to DeckGenerateRequest, T04 adds synergy fields to DeckEvaluationResponse. Both in Wave 1 but touch different schema classes (no conflict).
- `frontend/src/types/api.ts` -- T06 and T07 both read this file. T05 adds GeneratedCard.synergy_score and DeckGenerateResult fields (backend types). T06 adds RoleCoverageEntry and DeckEvaluation synergy fields. T07 consumes them read-only.
- i18n JSON files -- T06 adds `deck.evaluation.*` and `deck.roles.*` keys. T07 adds `deck.synergy.*` keys (different namespaces, no overlap). T07 must merge from T06's output before committing i18n changes.

## Waves

### Wave 0 -- Data Layer + Pure Logic (parallel, no deps)
| Task | Type | Description |
|------|------|-------------|
| T01  | backend | Add `oracle_text` column to CardRow + migration + update seeder |
| T02  | backend | Create `src/decks/synergy.py` -- keyword extraction + scoring engine |

T01 and T02 are fully independent: T01 touches models/seeder/scryfall, T02 creates a new pure module with zero imports from the codebase.

### Wave 1 -- Integration (depends on Wave 0)
| Task | Type | Depends on | Description |
|------|------|------------|-------------|
| T03  | backend | T01, T02 | Integrate synergy scoring into builder.py |
| T04  | backend | T02 | Update evaluator.py + suggestions.py with role validation + synergy metrics |
| T05  | backend | T02 | Add synergy_weight to DeckBuildParams + API endpoint |

T03 depends on both T01 (oracle_text available in DB) and T02 (synergy module exists).
T04 depends on T02 (uses classify_card_role from synergy.py) but not T01.
T05 depends on T02 (uses synergy_weight concept) but not T01.
T03, T04, T05 modify different files -- parallel-safe within Wave 1.

### Wave 2 -- Frontend (depends on Wave 1)
| Task | Type | Depends on | Description |
|------|------|------------|-------------|
| T06  | frontend | T04, T05 | Update DeckEvaluationPanel with synergy score + role breakdown |
| T07  | frontend | T03, T05 | Add synergy badges per card in DeckBuildWizard review step |

T06 depends on T04 (synergy metrics in evaluation response) and T05 (API schema).
T07 depends on T03 (synergy_score in card dicts) and T05 (API schema).
T06 and T07 modify different components -- parallel-safe within Wave 2.
T06 owns i18n file edits and TypeScript type additions. T07 reads them.

## Diagrams

Two Mermaid diagrams will be produced:
1. `docs/diagrams/F188-architecture.mmd` -- data flow from Scryfall oracle_text through synergy engine to frontend
2. `docs/diagrams/F188-journey.mmd` -- user journey for building a synergy-aware deck

# F133 — Deck Builder & Evaluator

**Status:** planned
**Priority:** P2
**Section:** Beta Test

## Description

Add deck building wizard and deck evaluation features to the Beta Test
section. The deck generator uses the Scryfall catalog (105K+ cards) to
build decks based on format, commander, archetype, colors, and budget.
The deck evaluator analyzes existing decks for mana curve, card type
distribution, color distribution, legality compliance, and budget
analysis, then produces actionable improvement suggestions.

## Goal

Let users (a) auto-generate decks from the catalog with intelligent
card selection and (b) evaluate any imported/generated deck against
format rules, archetype templates, and best-practice heuristics. Both
features live in the Beta Test nav section and reuse existing deck
models (DeckRow, DeckCardRow), catalog data (CardRow), legality data
(card_legalities), and charting (Recharts).

## Existing Infrastructure

| Component | Location | Notes |
|---|---|---|
| Deck models | `src/database/models.py` | DeckRow, DeckCardRow (FK to cards) |
| Deck services | `src/decks/` | importer.py, parser.py, valuation.py |
| Deck API | `src/api/routers/decks.py` | import, list, detail, ranking, value, delete |
| Deck pages | `frontend/src/pages/` | DeckList.tsx, DeckView.tsx, TopDecksPage.tsx |
| Catalog | CardRow (105K+ cards) | type_line, color_identity, mana_cost, rarity, image_uri |
| Legality | card_legalities table | card_id + format + status (legal/banned/restricted/not_legal) |
| Charts | Recharts | Already used in DeckView (AreaChart), PortfolioDashboard |
| Repository | `src/database/repository.py` | get_legalities_for_cards_batch, get_legalities_for_card, etc. |
| Nav | Layout.tsx BETA_NAV_ITEMS | Collapsible Beta Test section in sidebar |

## Wave Plan

### Wave 0 — Backend Services (parallel)

| Task | Summary |
|---|---|
| T01 | Deck evaluator service (`src/decks/evaluator.py`) |
| T02 | Deck builder service (`src/decks/builder.py`) |

### Wave 1 — Endpoints + Frontend (parallel, depends on Wave 0)

| Task | Summary |
|---|---|
| T03 | Evaluator endpoint + DeckView evaluation panel |
| T04 | Generator endpoint + frontend wizard page |

### Wave 2 — Suggestions + Integration (depends on Wave 1)

| Task | Summary |
|---|---|
| T05 | Suggestion engine with archetype templates |
| T06 | Navigation + integration (Beta Test nav, DeckView evaluation tab) |

## Out of Scope

- Multiplayer-specific analysis (e.g., pod synergy)
- Sideboard generation
- AI/LLM-powered card recommendations
- Card synergy detection beyond archetype templates
- Moxfield/Archidekt import (existing text/CSV import covers this)

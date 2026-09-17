# F133-T05: Suggestion Engine

**Wave:** 2
**Status:** planned
**Depends on:** F133-T01, F133-T03

## User Story

As a user, I want the deck evaluator to flag issues and suggest
improvements based on best-practice heuristics and archetype templates
so that I can quickly see what my deck is missing or has too much of.

## Description

Create `src/decks/suggestions.py` with archetype template data and a
suggestion engine that compares a DeckEvaluation result against known
good ratios, then returns actionable feedback strings. Integrate the
suggestions into the evaluator pipeline so they appear in the
evaluation response.

## Archetype Templates Data

Define `ARCHETYPE_TEMPLATES` as a module-level dict in
`src/decks/suggestions.py`:

```python
ARCHETYPE_TEMPLATES = {
    "commander": {
        "aggro": {
            "land_range": (34, 38),
            "creature_range": (28, 35),
            "instant_range": (6, 12),
            "sorcery_range": (4, 8),
            "enchantment_range": (3, 8),
            "artifact_range": (8, 15),
            "removal_min": 8,
            "card_draw_min": 8,
            "ramp_min": 8,
            "avg_cmc_range": (2.0, 3.2),
        },
        "control": {
            "land_range": (36, 40),
            "creature_range": (8, 16),
            "instant_range": (12, 18),
            "sorcery_range": (6, 12),
            "enchantment_range": (5, 12),
            "artifact_range": (8, 15),
            "removal_min": 10,
            "card_draw_min": 10,
            "ramp_min": 8,
            "avg_cmc_range": (2.5, 3.8),
        },
        "midrange": {
            "land_range": (35, 39),
            "creature_range": (20, 28),
            "instant_range": (6, 12),
            "sorcery_range": (5, 10),
            "enchantment_range": (4, 10),
            "artifact_range": (8, 14),
            "removal_min": 8,
            "card_draw_min": 8,
            "ramp_min": 10,
            "avg_cmc_range": (2.5, 3.5),
        },
        "combo": {
            "land_range": (34, 38),
            "creature_range": (14, 22),
            "instant_range": (8, 14),
            "sorcery_range": (8, 14),
            "enchantment_range": (5, 12),
            "artifact_range": (10, 18),
            "removal_min": 6,
            "card_draw_min": 10,
            "ramp_min": 10,
            "avg_cmc_range": (2.0, 3.2),
        },
        "tempo": {
            "land_range": (34, 38),
            "creature_range": (20, 28),
            "instant_range": (10, 16),
            "sorcery_range": (4, 8),
            "enchantment_range": (3, 8),
            "artifact_range": (8, 14),
            "removal_min": 8,
            "card_draw_min": 8,
            "ramp_min": 8,
            "avg_cmc_range": (1.8, 2.8),
        },
    },
}
```

Note: Only commander templates initially. Standard/modern can be added
later with the same structure but scaled to 60 cards.

## Functions to Implement

### `generate_suggestions(evaluation, archetype, format_name) -> list[str]`

Accepts a `DeckEvaluation` and optional archetype/format. Returns a
list of human-readable suggestion strings. All strings must be i18n-
friendly (English keys that the frontend can translate if needed, but
initially plain English text is fine).

Checks (in priority order):

1. **Card count** — if total_cards != expected (100 for commander,
   60 for standard/modern): "Deck has {n} cards, expected {expected}
   for {format}."

2. **Too few lands** — if land_count < template.land_range[0]:
   "Consider adding {n} more lands. {archetype} decks in {format}
   typically run {min}-{max} lands."

3. **Too many lands** — if land_count > template.land_range[1]:
   "Consider cutting {n} lands. You have {count} but {archetype}
   decks typically run {min}-{max}."

4. **Creature count** — same range check with template.creature_range

5. **Average CMC too high** — if avg_cmc > template.avg_cmc_range[1]:
   "Average mana cost is {cmc:.1f}, which is high for {archetype}.
   Consider adding more low-cost cards."

6. **Average CMC too low** — if avg_cmc < template.avg_cmc_range[0]:
   "Average mana cost is {cmc:.1f}. For a {archetype} deck, consider
   adding some higher-impact spells."

7. **Color balance** — if deck uses 3+ colors and any one color has
   <10% of total pips: "Color {X} has very few cards. Consider adding
   more {X} cards or removing it from the color identity."

8. **No interaction** — if instant_count < 4:
   "Very few instant-speed answers. Consider adding counterspells,
   removal, or combat tricks."

9. **Singleton violation** — if legality_check has
   singleton_violations (commander): "Cards appearing more than once:
   {list}. Commander decks are singleton."

10. **Banned cards** — if legality_check has illegal_cards:
    "{n} cards are not legal in {format}: {list}."

11. **Unlinked cards** — count cards without card_id:
    "Deck has {n} unresolved cards. These cards could not be matched
    to the catalog and are excluded from the analysis."

### `_in_range(value, range_tuple) -> str | None`

Helper: returns "low"/"high"/None for out-of-range values.

## Integration

Modify `src/decks/evaluator.py` `evaluate_deck()`:
- After computing the DeckEvaluation, call
  `generate_suggestions(evaluation, archetype, format_name)`
- Populate `evaluation.suggestions` with the result
- The archetype parameter comes from DeckRow.description (if it
  contains a known archetype keyword) or from a new optional param
  on the evaluator endpoint

Modify `GET /api/v1/decks/{deck_id}/evaluate`:
- Add optional `archetype` query param (str, default None)
- Pass to evaluator for template matching
- If not provided, suggestions still run with generic heuristics
  (card count, land count, CMC, legality only)

## Dev Notes

- Templates are intentionally conservative ranges. The goal is to
  flag obvious issues, not enforce a specific deck style.
- Suggestion strings are plain English. If i18n is needed later, they
  can be converted to key+params format.
- The removal_min / card_draw_min / ramp_min template fields are
  defined but NOT checked in v1 — detecting whether a card is
  "removal" or "card draw" requires keyword analysis of card text
  (oracle text), which we don't store. These fields are placeholders
  for future enhancement.
- Keep suggestions sorted by severity (card count / legality issues
  first, optimization suggestions last).

## Testing

- Test each suggestion trigger individually: too few lands, too many
  lands, high CMC, low CMC, singleton violation, banned card, etc.
- Test that a "perfect" deck (within all ranges) returns empty list
- Test with no archetype -> only generic checks run (card count,
  legality, unlinked)
- Test with archetype "aggro" -> creature range checks use aggro
  template
- Test unknown archetype -> falls back to generic checks
- Test unknown format -> no template match, generic only
- Test integration: evaluator populates suggestions field
- Target: 15+ tests

# F133-T02: Deck Builder Backend Service

**Wave:** 0
**Status:** planned
**Depends on:** none

## User Story

As a user, I want to auto-generate a deck from the card catalog based
on my chosen format, colors, archetype, and budget so that I get a
playable starting point without manually selecting each card.

## Description

Create `src/decks/builder.py` — a service module that queries the
catalog (via Repository) to build a deck matching the user's
parameters. The builder is format-aware (commander has 100 cards
singleton, standard/modern have 60 cards with 4-of limit) and uses
heuristic rules for card selection.

## Functions to Implement

### `generate_deck(repo, params) -> GeneratedDeck`

Main entry point. Accepts a Repository instance and a
`DeckBuildParams` dataclass.

`DeckBuildParams` fields:
- `format_name`: str ("commander", "standard", "modern", "legacy",
  "pauper", "casual") — required
- `commander_card_id`: int | None — for commander format, the
  commander card (determines color identity)
- `colors`: list[str] — e.g. ["W", "U"]; ignored if commander
  provided (derived from commander's color_identity)
- `archetype`: str | None — "aggro", "control", "combo",
  "midrange", "tempo" (affects card selection ratios)
- `budget_limit`: Decimal | None — max total deck value in BRL
- `prioritize_owned`: bool — if True, prefer cards user already owns
- `user_id`: str | None — needed for owned-card lookup
- `exclude_card_ids`: list[int] — cards to exclude

Returns a `GeneratedDeck` dataclass:
- `cards`: list of dicts {card_id, name_en, set_code,
  collector_number, quantity, mana_cost, type_line, rarity,
  image_uri, price, is_owned}
- `format_name`: str
- `archetype`: str | None
- `colors`: list[str]
- `total_value`: Decimal | None
- `land_count`: int
- `nonland_count`: int
- `warnings`: list[str] — any issues (e.g. "Not enough cards in
  color identity", "Budget exceeded")

### Internal helpers

#### `_get_target_composition(format_name, archetype) -> dict`

Return target card type ratios based on format and archetype:

| Archetype | Lands | Creatures | Instants | Sorceries | Enchantments | Artifacts | Planeswalkers |
|---|---|---|---|---|---|---|---|
| aggro | 36 | 30 | 8 | 6 | 4 | 10 | 0 |
| control | 38 | 10 | 14 | 8 | 8 | 10 | 4 |
| midrange | 37 | 24 | 8 | 8 | 6 | 10 | 2 |
| combo | 36 | 16 | 10 | 12 | 8 | 12 | 0 |
| tempo | 36 | 22 | 14 | 6 | 4 | 10 | 2 |
| None/casual | 37 | 24 | 8 | 6 | 6 | 10 | 2 |

Values shown for commander (100 cards). For 60-card formats, scale
proportionally (multiply by 0.6, round, ensure sum = 60).

#### `_query_candidates(repo, colors, format_name, card_type, limit) -> list`

Query CardRow table filtered by:
- `color_identity` subset of allowed colors (parse stored string,
  every letter must be in allowed set)
- Cards legal in format (JOIN card_legalities WHERE format=format_name
  AND status='legal')
- `type_line` matches target card type
- Exclude basic lands (those are added separately)
- Order by: rarity priority (M > R > U > C for control/midrange,
  C > U > R > M for aggro/tempo), then by price if budget matters

#### `_select_cards(candidates, target_count, singleton, budget_remaining, owned_ids) -> list`

Pick cards from candidates:
- If singleton: pick 1 of each, prefer owned, respect budget
- If not singleton: pick up to 4 of each, prefer cheaper printings
- Stop when target_count reached or candidates exhausted

#### `_add_lands(colors, land_count, format_name, singleton) -> list`

Add basic lands proportional to color pip distribution.
For commander: also add Command Tower, Sol Ring, Arcane Signet if
legal and within budget. For multi-color decks: add some dual
lands / fetch lands from catalog if available.

## Domain Model

Add to `src/domain/models.py`:

```python
@dataclass
class DeckBuildParams:
    format_name: str
    commander_card_id: int | None = None
    colors: list[str] = field(default_factory=list)
    archetype: str | None = None
    budget_limit: Decimal | None = None
    prioritize_owned: bool = False
    user_id: str | None = None
    exclude_card_ids: list[int] = field(default_factory=list)

@dataclass
class GeneratedDeck:
    cards: list[dict]
    format_name: str
    archetype: str | None
    colors: list[str]
    total_value: Decimal | None
    land_count: int
    nonland_count: int
    warnings: list[str] = field(default_factory=list)
```

## Dev Notes

- The builder uses Repository for DB queries (unlike evaluator which
  is pure). This is necessary because it needs to query the full
  catalog, which is too large to pass in-memory.
- Color identity filtering: a card with color_identity "WU" is
  allowed in a "WUB" deck but not in a "WR" deck. Parse the stored
  string (e.g. "WUBRG", "R", "", "C") and check subset.
- Commander-specific: exactly 100 cards, singleton (except basic
  lands), commander determines color identity.
- Standard/Modern: 60 cards, max 4 copies (except basic lands).
- For `prioritize_owned`, query user_collection to get the user's
  owned card_ids, then sort candidates to prefer those.
- Budget enforcement: track running total, skip expensive cards when
  budget_remaining < card price. Add warning if budget caused
  sub-optimal picks.
- Basic lands should use a canonical card_id from the catalog (e.g.,
  the FDN printing of each basic land type).
- The function may return fewer than target cards if the catalog
  doesn't have enough legal cards in the color identity. Add a
  warning in that case.

## Testing

- Unit test `_get_target_composition`: verify sums (100 for commander,
  60 for standard), each archetype returns valid dict
- Unit test `_query_candidates` with mock repo: verify color filtering,
  legality filtering, type filtering
- Unit test `_select_cards`: singleton mode picks 1-of-each, budget
  mode skips expensive cards, owned preference works
- Integration test `generate_deck` with in-memory SQLite: seed 200
  cards across colors, generate a commander deck, verify 100 cards,
  singleton, color identity respected
- Test edge case: no cards in color -> returns partial deck + warning
- Test budget_limit: total_value <= budget_limit when possible
- Test commander format: commander_card_id sets color identity
- Target: 20+ tests

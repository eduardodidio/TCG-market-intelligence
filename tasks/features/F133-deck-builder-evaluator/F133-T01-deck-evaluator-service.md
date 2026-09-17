# F133-T01: Deck Evaluator Backend Service

**Wave:** 0
**Status:** planned
**Depends on:** none

## User Story

As a user, I want the system to analyze my deck composition so that I
can understand its mana curve, color distribution, type distribution,
legality compliance, and budget breakdown without manually counting
cards.

## Description

Create `src/decks/evaluator.py` — a pure service module (no DB imports,
receives data as arguments) that computes deck evaluation metrics from
a list of card data dicts and optional price/legality maps.

## Functions to Implement

### `evaluate_deck(cards, prices, legalities, format_name) -> DeckEvaluation`

Main entry point. Accepts:
- `cards`: list of dicts, each with keys `card_id`, `quantity`,
  `name_en`, `mana_cost`, `type_line`, `color_identity`, `rarity`
- `prices`: dict mapping card_id -> Decimal price (optional)
- `legalities`: dict mapping card_id -> list of {format, status} dicts
- `format_name`: str (e.g. "commander", "standard", "modern") or None

Returns a `DeckEvaluation` dataclass with:

1. **mana_curve** — dict mapping CMC (0-7+) to card count. Parse mana
   cost string `{2}{W}{W}` into CMC (sum numeric + count pips). Land
   cards (type_line contains "Land") excluded from curve.

2. **color_distribution** — dict mapping color letter (W, U, B, R, G,
   C for colorless) to pip count across all non-land cards. Derived
   from mana_cost, not color_identity.

3. **type_distribution** — dict mapping primary type (Creature,
   Instant, Sorcery, Enchantment, Artifact, Planeswalker, Land,
   Other) to card count. Parse type_line, split on " -- " or
   " — " to get supertypes, use first recognized type.

4. **land_count** — int, total lands (quantity-weighted)

5. **nonland_count** — int, total non-lands (quantity-weighted)

6. **total_cards** — int (quantity-weighted sum)

7. **avg_cmc** — float, average CMC of non-land cards (weighted by qty)

8. **color_identity** — set of color letters from all cards'
   color_identity fields (union)

9. **legality_check** — if format_name provided, dict with:
   - `format`: str
   - `is_legal`: bool (all cards legal in format)
   - `illegal_cards`: list of {name_en, status} for cards that are
     banned/not_legal/restricted
   - `singleton_violations`: list of card names appearing >1 time
     (for commander format)
   - `card_count_valid`: bool (100 for commander, 60 for standard/
     modern, no limit otherwise)

10. **budget** — if prices provided, dict with:
    - `total_value`: Decimal
    - `most_expensive`: list of top 5 {name_en, price, quantity}
    - `price_tiers`: dict mapping tier label to count
      ("budget" <5, "mid" 5-20, "premium" 20-50, "chase" >50 BRL)

### `parse_cmc(mana_cost: str | None) -> int`

Parse a mana_cost string like `{3}{U}{U}` into converted mana cost.
Return 0 for None/empty. Handle: `{X}` = 0, `{N}` = N,
color pips `{W}`, `{U}`, `{B}`, `{R}`, `{G}` = 1 each,
hybrid `{W/U}` = 1, phyrexian `{W/P}` = 1.

### `classify_card_type(type_line: str | None) -> str`

Return primary type from type_line. Priority order: Land, Creature,
Planeswalker, Instant, Sorcery, Enchantment, Artifact, Other.
Handle double-faced cards (split on " // ") and use front face.

## Domain Model

Add to `src/domain/models.py`:

```python
@dataclass
class DeckEvaluation:
    mana_curve: dict[int, int]
    color_distribution: dict[str, int]
    type_distribution: dict[str, int]
    land_count: int
    nonland_count: int
    total_cards: int
    avg_cmc: float
    color_identity: set[str]
    legality_check: dict | None = None
    budget: dict | None = None
    suggestions: list[str] = field(default_factory=list)
```

## Dev Notes

- Keep the module pure (no SQLAlchemy, no Repository). It receives
  pre-fetched data and returns computed results. This makes it trivially
  testable.
- Mana cost parsing must handle edge cases: split cards (`{3}{U} // {1}{R}`
  use front face only), X costs, hybrid mana, phyrexian mana.
- The `cards` list structure mirrors what the API endpoint (T03) will
  assemble from DeckCardRow JOIN CardRow.
- Follow the same pattern as `src/decks/valuation.py` (pure functions,
  dataclass results).

## Testing

- Unit test `parse_cmc` with: `{3}{U}{U}` -> 5, `{X}{R}` -> 1,
  `{W/U}{B}` -> 2, `None` -> 0, `""` -> 0, `{0}` -> 0
- Unit test `classify_card_type` with: "Legendary Creature — Dragon" ->
  "Creature", "Instant" -> "Instant", "Artifact Land" -> "Land",
  "Enchantment Creature — God" -> "Creature", None -> "Other",
  "Creature // Instant" -> "Creature" (front face)
- Unit test `evaluate_deck` with a 10-card mock deck: verify mana_curve
  totals, type_distribution sums to nonland+land, avg_cmc calculation
- Test legality_check: one banned card in commander -> is_legal=False,
  illegal_cards has 1 entry
- Test singleton violations: two copies of same card in commander deck
- Test budget tiers: verify price tier counts sum to total priced cards
- Test edge case: empty deck -> all zeroes, no crash
- Target: 25+ unit tests

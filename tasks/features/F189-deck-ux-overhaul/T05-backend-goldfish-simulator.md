# F189-T05 — Backend: Goldfish simulator service + endpoint

**Feature:** F192
**Wave:** 1
**Status:** planned
**Parallel:** yes (fully independent of T03, T04, T06)

## User Story

As a deck builder, I want to simulate goldfishing my deck (playing solitaire draws) so I can analyze the mana curve quality, opening hand consistency, and identify mana screw/flood tendencies before playing real games.

## Dev Notes

### Files to CREATE

**`src/decks/goldfish.py`**
Pure-function module with no database imports. Receives card data as input.

Core functions:
- `simulate_goldfish(cards: list[dict], num_simulations: int = 100, turns: int = 7) -> GoldfishResult`
  - `cards` is a list of dicts with keys: `name_en`, `quantity`, `type_line`, `mana_cost`
  - Expands the deck list according to quantities (e.g., 4x Lightning Bolt = 4 entries)
  - Runs `num_simulations` independent games
  - Aggregates results into GoldfishResult

- `_simulate_single_game(deck_list: list[dict], turns: int) -> SingleGameResult`
  - Shuffles the expanded deck (use `random.shuffle` on a copy)
  - Draws 7 cards for opening hand
  - For each turn 1..turns:
    - Draw 1 card (turn 1 skips draw on the play -- optional simplification: always draw)
    - Play 1 land if available in hand (prioritize by color diversity or just first land)
    - Count how many non-land spells in hand are castable (CMC <= available mana)
    - Track: lands_in_play, spells_cast_this_turn, total_spells_cast
  - Returns per-turn data

- `_evaluate_opening_hand(hand: list[dict]) -> float`
  - Quality score 0.0 to 1.0
  - Factors: land count (ideal 2-3 for 7 cards), curve presence (has 1-2 CMC spell), color diversity
  - Simple heuristic: 0 lands = 0.0, 1 land = 0.3, 2 lands = 0.9, 3 lands = 1.0, 4 lands = 0.7, 5 lands = 0.3, 6+ lands = 0.1
  - Bonus +0.1 if hand contains a spell with CMC <= 2 (capped at 1.0)

- `_is_land(type_line: str | None) -> bool`
  - Returns True if type_line contains "Land" (case-insensitive)
  - Handles None gracefully (returns False)

- `_parse_cmc_simple(mana_cost: str | None) -> int`
  - Parses mana cost string like "{2}{U}{U}" into CMC (total mana value)
  - Generic mana: extract number from `{N}` symbols
  - Color pips: each `{W}`, `{U}`, `{B}`, `{R}`, `{G}` counts as 1
  - Hybrid: `{W/U}` counts as 1
  - X costs: `{X}` counts as 0
  - Returns 0 for None or empty string

Dataclasses:
```python
@dataclass
class TurnData:
    turn: int
    lands_in_play: int
    spells_castable: int
    spells_cast: int
    cards_in_hand: int

@dataclass
class SingleGameResult:
    opening_hand_quality: float
    opening_hand_lands: int
    turns: list[TurnData]

@dataclass
class SampleHand:
    cards: list[str]  # card names
    quality: float
    land_count: int

@dataclass
class GoldfishResult:
    opening_hand_quality: float      # avg across all simulations
    avg_mana_by_turn: list[float]    # index 0 = turn 1
    mana_screw_rate: float           # 0.0-1.0
    mana_flood_rate: float           # 0.0-1.0
    avg_spells_cast_by_turn: list[float]  # index 0 = turn 1
    sample_hands: list[SampleHand]   # 3 representative hands
    total_simulations: int
    total_turns: int
```

Mana screw definition:
- Opening hand has <= 1 land, OR
- By turn 4, total lands in play <= 2

Mana flood definition:
- Opening hand has >= 5 lands, OR
- By turn 7, lands drawn / total cards drawn >= 0.70

Sample hands: pick 3 from the simulations -- one good (highest quality), one bad (lowest quality), one median.

### Files to MODIFY

**`src/api/routers/decks.py`**
- Add `POST /decks/{deck_id}/goldfish` endpoint:
  ```python
  @router.post("/{deck_id}/goldfish", response_model=ApiResponse[GoldfishResponse])
  def goldfish_deck(
      deck_id: int,
      num_simulations: int = Query(default=100, ge=10, le=1000),
      turns: int = Query(default=7, ge=3, le=15),
      repo: Repository = Depends(get_db),
      user_id: str = Depends(require_auth_or_api_key),
  ):
  ```
  - Fetches deck + deck_cards from repo
  - Enriches cards with type_line and mana_cost from card_info (similar to evaluate endpoint)
  - Calls `simulate_goldfish(enriched_cards, num_simulations, turns)`
  - Returns GoldfishResponse

**`src/api/schemas/decks.py`**
- Add Pydantic response schemas:
  ```python
  class GoldfishSampleHand(BaseModel):
      cards: list[str]
      quality: float
      land_count: int

  class GoldfishResponse(BaseModel):
      deck_id: int
      opening_hand_quality: float
      avg_mana_by_turn: list[float]
      mana_screw_rate: float
      mana_flood_rate: float
      avg_spells_cast_by_turn: list[float]
      sample_hands: list[GoldfishSampleHand]
      total_simulations: int
      total_turns: int
  ```

### Key constraints
- `goldfish.py` must be a PURE module (no database imports, no FastAPI imports). It receives data, returns results. This enables easy unit testing.
- Use `random.shuffle` for deck shuffling. For reproducibility in tests, accept an optional `rng: random.Random | None` parameter.
- Performance: 100 simulations x 7 turns should complete in < 100ms for a 100-card deck. No heavy computation involved.
- The endpoint must verify deck ownership (same pattern as evaluate/get_deck).

### Edge cases
- Deck with 0 cards: return error (400, "Deck has no cards to simulate")
- Deck with all lands: mana_flood_rate should be 1.0, no spells cast
- Deck with no lands: mana_screw_rate should be 1.0, no mana available
- Cards with no type_line (unlinked): assume non-land, CMC 0
- Cards with no mana_cost (lands typically have none): CMC 0, correctly identified as land via type_line
- Deck smaller than 7 cards: draw min(7, deck_size) for opening hand

## Testing

- [ ] Unit test: `_is_land("Legendary Land -- Desert")` returns True
- [ ] Unit test: `_is_land("Creature -- Elf Warrior")` returns False
- [ ] Unit test: `_is_land(None)` returns False
- [ ] Unit test: `_parse_cmc_simple("{3}{U}{U}")` returns 5
- [ ] Unit test: `_parse_cmc_simple("{X}{R}")` returns 1 (X=0)
- [ ] Unit test: `_parse_cmc_simple(None)` returns 0
- [ ] Unit test: `_parse_cmc_simple("{W/U}{W/U}")` returns 2
- [ ] Unit test: `_evaluate_opening_hand` with 0 lands returns 0.0
- [ ] Unit test: `_evaluate_opening_hand` with 3 lands returns ~1.0
- [ ] Unit test: `_evaluate_opening_hand` with 6 lands returns ~0.1
- [ ] Unit test: `simulate_goldfish` with all-lands deck returns flood_rate = 1.0
- [ ] Unit test: `simulate_goldfish` with no-lands deck returns screw_rate = 1.0
- [ ] Unit test: `simulate_goldfish` returns correct number of sample_hands (3)
- [ ] Unit test: `simulate_goldfish` with deterministic RNG produces reproducible results
- [ ] Unit test: `simulate_goldfish` with normal deck returns reasonable rates (screw < 0.5, flood < 0.5)
- [ ] Unit test: avg_mana_by_turn is monotonically non-decreasing
- [ ] Integration test: `POST /decks/{id}/goldfish` returns 200 with valid response
- [ ] Integration test: `POST /decks/{id}/goldfish` on nonexistent deck returns 404
- [ ] Integration test: `POST /decks/{id}/goldfish` on another user's deck returns 404
- [ ] Integration test: `POST /decks/{id}/goldfish` on empty deck returns 400
- [ ] Integration test: query params `num_simulations=10&turns=5` are respected

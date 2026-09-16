# F129 -- Liga Price Accuracy: Validate & Fix Remaining Divergences

**Status:** planned
**Branch:** homol
**Ground truth:** 460 cards from 7 HTML files in `docs/htmlsColecao/`

## Problem Statement

A comparison of 460 collection cards against Liga Magic's own collection HTML
exports shows massive price divergences:

| Status        | Count | % of total |
|---------------|------:|------------|
| BIG_MISMATCH  |   273 |       59%  |
| MISMATCH      |    89 |       19%  |
| DRIFT         |    57 |       12%  |
| OK            |    26 |        6%  |
| NOT_IN_DB     |    15 |        3%  |

The comparison uses Liga's "Menor Preco de Compra" (lowest buy price) against
our stored "mid" (market median). Our mid being higher than Liga's lowest buy
is **expected** for most cards. The data-sigla edition disambiguation fix
shipped (commit 1686d03), but the comparison data is from **before** a fresh
sweep with the fix active.

### Key findings from pre-fix data analysis

1. **266 positive BIG_MISMATCH** (our price > Liga lowest buy, >50%): Most of
   these are expected (mid vs lowest buy), but some are 500%--26000% deviations
   caused by wrong edition selection (pre-fix data).

2. **7 negative BIG_MISMATCH** (our price < Liga lowest buy): These are genuine
   bugs -- our price should never be lower than Liga's lowest buy. Root causes:
   wrong edition stored, foil/non-foil confusion, variant mismatch.

3. **15 NOT_IN_DB**: All 15 cards have diacritical characters in their names
   (Dain, Anduril, Barad-dur, Kili, Fili, Oin, etc.). The comparison script's
   ILIKE match fails on these characters. This is a **tooling bug**, not a
   price bug.

4. **Double-face cards** (// in name): Some show extreme deviations (e.g.
   Thranduil 26226%, Bilbo Luckwearer 3761%, Arkenstone 690%). The URL builder
   correctly uses front-face only, but edition selection may be picking wrong
   printings.

5. **Extreme positive outliers** (>500%): Sol Ring +1690%, Orb of Dragonkind
   +3033%, Inferno of Star Mounts +1041%, Goblin Bushwhacker +900%. These are
   likely wrong-edition prices from pre-fix sweep data.

## Acceptance Criteria

- After full sweep + fixes, >80% of cards should be OK or DRIFT (within 20%)
- Cards where our price < Liga's lowest buy should be 0
- No card should have >10x deviation unless genuinely different edition/variant
- Comparison script produces automated validation report with clear bucketing

## Wave Strategy

### Wave 0 -- Tooling (2 tasks, parallel)
Enhance comparison + debug scripts for automated post-sweep validation.

| Task | Description |
|------|-------------|
| T01  | Enhance comparison script: diacritics matching, directional status, summary report |
| T02  | Enhance debug script: set_code support, batch mode for investigating mismatches |

### Wave 1 -- Analysis Sweep (1 task, user-driven)
User runs fresh sweep + comparison. This is a MANUAL step.

| Task | Description |
|------|-------------|
| T03  | Document the re-sweep + re-compare procedure, classify divergence buckets |

### Wave 2 -- Fixes (3 tasks, parallel)
Implement fixes for each identified divergence pattern.

| Task | Description |
|------|-------------|
| T04  | Set code normalization mapping (Scryfall set_code -> Liga sigla) |
| T05  | Double-face / split card name handling improvements |
| T06  | Foil edition fallback + variant edition matching improvements |

### Wave 3 -- Validation (1 task)
Final sweep + comparison proving accuracy targets met.

| Task | Description |
|------|-------------|
| T07  | Post-fix validation sweep and accuracy report |

## Key Files

- `src/providers/liga/parser.py` -- parse_edition_options (3-tuple with sigla)
- `src/providers/liga/provider.py` -- _select_edition (data-sigla disambiguation)
- `src/collectors/liga_sweep.py` -- _fetch_liga_price (passes set_code)
- `src/providers/liga/url.py` -- liga_url_for_card_name
- `scripts/liga_collection_compare.py` -- comparison engine
- `scripts/liga_debug.py` -- debug tool

## Constraints

- Liga blocks datacenter IPs -- sweep must run from user's Windows machine
- Comparison uses Liga "lowest buy" vs our "mid" -- expected difference
- The data-sigla fix is already shipped (commit 1686d03)
- Ground truth: 460 cards from 7 HTML files in `docs/htmlsColecao/`

# F129 -- Liga Price Accuracy Report

**Date:** 2026-09-16
**Branch:** homol
**Ground truth:** ~460 cards from 7 HTML files in `docs/htmlsColecao/`

---

## Methodology

- Liga collection HTML exports show "Menor Preco de Compra" (lowest buy
  price) -- the cheapest individual listing on Liga Magic.
- Our database stores "mid" (market median from Liga's price bar chart).
- Our mid being HIGHER than Liga's lowest buy is **structurally expected**
  for most cards. The lowest buy is a single seller's floor price; the mid
  reflects the market median across all listings.
- The comparison uses the enhanced script (`scripts/liga_collection_compare.py`)
  with directional status (ABOVE/BELOW) and root-cause hint classification.
- Thresholds: <5% = OK, 5-20% = DRIFT, 20-50% = MISMATCH, >50% = BIG.

---

## Before Fix (Pre data-sigla, pre F129)

Snapshot taken from the initial comparison before any F129 fixes or the
data-sigla edition disambiguation fix. This represents the baseline state.

| Status        | Count | % of total |
|---------------|------:|------------|
| BIG_MISMATCH  |   273 |       59%  |
| MISMATCH      |    89 |       19%  |
| DRIFT         |    57 |       12%  |
| OK            |    26 |        6%  |
| NOT_IN_DB     |    15 |        3%  |
| **Total**     |   460 |      100%  |

### Key issues identified

1. **15 NOT_IN_DB** -- all 15 cards have diacritical characters (LOTR/Hobbit
   set: Dain, Anduril, Barad-dur, Kili, Fili, Oin, etc.). The comparison
   script's ILIKE match failed on these characters. This was a **tooling bug**
   in the comparison script, not a price bug.

2. **No directional status** -- BIG_MISMATCH did not distinguish between
   "our price > Liga" (potentially expected) and "our price < Liga" (genuine
   bug). All 273 were lumped together.

3. **7 negative BIG_MISMATCH** (our price < Liga lowest buy) -- genuine bugs
   where our stored price was lower than Liga's floor. Root causes: wrong
   edition stored, foil/non-foil confusion, variant mismatch.

4. **Extreme positive outliers** -- Sol Ring +1690%, Orb of Dragonkind +3033%,
   Inferno of Star Mounts +1041%, Goblin Bushwhacker +900%. These were
   wrong-edition prices caused by ambiguous collector_number matching
   across multiple printings.

5. **Double-face cards** -- Thranduil +26226%, Bilbo Luckwearer +3761%,
   Arkenstone +690%. Edition selection was picking wrong printings for DFC
   cards.

---

## After Data-Sigla Fix + F129 Wave 0-2 Fixes

> **TO BE FILLED after running validation sweep.**
>
> Follow the procedure in `docs/procedures/liga-accuracy-validation.md`:
>
> ```bash
> # 1. Force full re-sweep with all fixes active
> python -m src.cli.main liga-sweep --max-age-days 0
>
> # 2. Run comparison against Liga HTML ground truth
> python scripts/liga_collection_compare.py
>
> # 3. Review output files:
> #    - scripts/debug_output/price_comparison.csv (full report)
> #    - scripts/debug_output/mismatches.csv (>20% deviations only)
> ```

### Status Breakdown

| Status           | Count | % of total |
|------------------|------:|------------|
| OK               |       |            |
| DRIFT            |       |            |
| MISMATCH_ABOVE   |       |            |
| MISMATCH_BELOW   |       |            |
| BIG_ABOVE        |       |            |
| BIG_BELOW        |       |            |
| NO_OUR_PRICE     |       |            |
| NO_LIGA_PRICE    |       |            |
| NOT_IN_DB        |       |            |
| **Total**        |       |            |

**OK + DRIFT:** ___ / ___ = ___%

### Root-Cause Hint Breakdown

| Hint         | Count | Notes |
|--------------|------:|-------|
| expected     |       | Positive diff, no other flags, Liga > R$5 -- normal mid-vs-buy spread |
| cheap_card   |       | Liga buy < R$1.00 -- noise, small absolute diff shows as high % |
| foil_card    |       | "Foil" in extras -- foil/non-foil price confusion |
| dfc_card     |       | Name contains " // " -- double-face card URL or edition issue |
| variant_ed   |       | Variant edition (Borderless, Showcase, Extended Art, Retro) |
| promo        |       | "Promo" or "Pre Release" in extras |
| art_card     |       | Art Series or Art Card -- typically no market price |
| (no hint)    |       | No heuristic applies -- needs manual investigation |

---

## Remaining Deviations

> List any cards still showing BIG_ABOVE or BIG_BELOW after all fixes,
> with root cause and whether it is:
>
> - **Expected** -- mid vs lowest-buy structural difference (our mid is
>   naturally higher than Liga's floor price)
> - **Cheap card noise** -- card < R$1.00 where small absolute differences
>   produce large percentage swings
> - **Genuine remaining issue** -- needs follow-up in a future feature

### BIG_BELOW (our price < Liga lowest buy)

> These are genuine bugs. Our mid should NEVER be below Liga's lowest buy.

| Card | Our Price | Liga Price | Diff % | Root Cause | Follow-up |
|------|----------:|----------:|-------:|------------|-----------|
|      |           |           |        |            |           |

### BIG_ABOVE with >10x deviation

> Cards where our price is more than 10x Liga's lowest buy. These need
> explanation -- usually wrong edition, variant confusion, or expected
> cheap card noise.

| Card | Our Price | Liga Price | Diff % | Hint | Explanation |
|------|----------:|----------:|-------:|------|-------------|
|      |           |           |        |      |             |

---

## Fixes Implemented in F129

### Wave 0 -- Tooling

| Task | Fix | Description |
|------|-----|-------------|
| T01  | Diacritics matching | `normalize_diacritics()` using `unicodedata.normalize('NFKD')` + strip combining chars. Applied to both Liga HTML names and DB query parameters. Resolves 15 NOT_IN_DB cards. |
| T01  | Directional status | BIG_MISMATCH split into BIG_ABOVE / BIG_BELOW. MISMATCH split into MISMATCH_ABOVE / MISMATCH_BELOW. Distinguishes expected (our > Liga) from bugs (our < Liga). |
| T01  | Root-cause hints | Heuristic `hint` column: foil_card, dfc_card, art_card, promo, variant_ed, cheap_card, expected. Enables automated triage of mismatches. |
| T02  | Debug batch mode | `--batch` flag reads CSV, processes multiple cards. `--set-code` triggers edition selection with sigla matching. `--limit N` caps batch size. Output to `scripts/debug_output/batch_debug.csv`. |

### Wave 1 -- Analysis (Manual)

| Task | Fix | Description |
|------|-----|-------------|
| T03  | Validation procedure | Step-by-step guide in `docs/procedures/liga-accuracy-validation.md`. Covers dry run, full sweep, comparison, classification, and decision matrix for Wave 2 scope. |

### Wave 2 -- Code Fixes

| Task | Fix | Description |
|------|-----|-------------|
| T04  | Sigla normalization | `normalize_sigla()` in `src/providers/liga/sigla_map.py`. Maps Scryfall set_code to Liga data-sigla for sets where they differ. Integrated into `_select_edition` before sigla comparison. |
| T05  | DFC name handling | Strip "(Art Card)", "(Borderless)", etc. from card names before Liga search. Collector number normalization: "32a" -> "32" for front-face DFC matching. |
| T06  | Variant sigla fallback | When exact sigla match fails, try common variant prefixes: `p{set}` (promo), `amp{set}` (ampersand promo), and unprefixed base set. Prevents silent edition selection failure for variant printings. |
| T06  | Foil diagnostic logging | Enhanced structured logging when foil card's edition is selected but no foil prices found. Fields: card, card_id, edition_value, set_code. Aids debugging without changing behavior. |

### Pre-F129 Fixes (already shipped)

| Commit | Fix | Description |
|--------|-----|-------------|
| `132ad2e` | data-sigla disambiguation | Edition selection compares `data-sigla` attribute against `set_code` to prevent wrong edition when multiple editions share the same collector number. |
| `1686d03` | Skip on edition failure | Returns None (skips price) when edition selection fails instead of using the default (potentially wrong) edition. Also strips `(#xxx)` annotations from card names. |
| `07c0087` | Structured price parsing | Parse prices from the structured `price-mkp` section instead of scanning the full page. More reliable extraction. |

---

## Acceptance Criteria

- [ ] >80% of cards are OK or DRIFT (within 20% of Liga lowest buy)
- [ ] 0 cards where our price < Liga's lowest buy (BIG_BELOW = 0)
- [ ] No card with >10x deviation unless documented as a known exception
- [ ] NOT_IN_DB count is 0 (diacritics fix working)

---

## Verdict

> **TO BE FILLED**
>
> **PASS** / **FAIL** / **PARTIAL** (with notes on follow-up needed)
>
> If PARTIAL, list follow-up items:
>
> | Issue | Severity | Proposed Follow-up |
> |-------|----------|--------------------|
> |       |          |                    |

---

## Appendix: How to Re-run This Validation

```bash
# Full sweep (all cards, no age filter)
python -m src.cli.main liga-sweep --max-age-days 0

# Run comparison
python scripts/liga_collection_compare.py

# Debug specific card
python scripts/liga_debug.py "Card Name" -cn 123 -sc fdn

# Debug batch of mismatches
python scripts/liga_debug.py --batch scripts/debug_output/mismatches.csv --limit 20
```

See `docs/procedures/liga-accuracy-validation.md` for the full step-by-step
procedure, timing estimates, and troubleshooting guidance.

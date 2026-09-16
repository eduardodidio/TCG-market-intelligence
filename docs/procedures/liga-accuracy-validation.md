# Liga Price Accuracy Validation Procedure

Step-by-step guide for running a full Liga sweep, comparing results against
the Liga collection HTML ground truth, classifying remaining divergences,
and deciding on further fixes.

**Feature:** F129 -- Liga Price Accuracy
**Ground truth:** ~460 cards from 7 HTML files in `docs/htmlsColecao/`
**Context:** The data-sigla edition disambiguation fix shipped in commit
`1686d03`. This procedure re-sweeps ALL collection cards through the fixed
code path and measures the improvement.

---

## Prerequisites

Before starting, confirm the following:

- [ ] Python environment with project dependencies installed
- [ ] Playwright installed: `playwright install chromium`
- [ ] `.env` file in project root with `DATABASE_URL` pointing to Neon PostgreSQL
- [ ] Machine on a **residential IP** (Liga blocks datacenter/VPN IPs)
- [ ] Liga collection HTML exports present in `docs/htmlsColecao/` (7 files)
- [ ] No other sweep or scan running concurrently

---

## Step 1 -- Dry Run (Estimate)

Run a dry run first to confirm the card count and verify connectivity:

```bash
python -m src.cli.main liga-sweep --max-age-days 0 --dry-run
```

Expected output: the number of eligible cards (approximately 560). If the
count is 0, check that `DATABASE_URL` in `.env` is correct and that the
user_collection table has data.

---

## Step 2 -- Full Sweep

Force ALL collection cards through the fixed code path:

```bash
python -m src.cli.main liga-sweep --max-age-days 0
```

### Timing and pacing

| Parameter        | Default | Description                         |
|------------------|---------|-------------------------------------|
| `--delay`        | 5.0     | Seconds between individual cards    |
| `--batch-size`   | 20      | Cards per batch before pausing      |
| `--batch-pause`  | 60      | Seconds to pause between batches    |
| `--max-age-days` | 7       | Skip cards priced within N days     |
| `--limit`        | (none)  | Max total cards to process          |
| `--set`          | (none)  | Only sweep a specific set code      |

With defaults (~560 cards, 5s delay, 20/batch, 60s pause):
- ~28 batches
- ~45-60 minutes total

### If interrupted

The sweep saves progress card-by-card. If interrupted with Ctrl+C, simply
re-run the same command. Cards already priced within the `max-age-days`
window will be skipped automatically.

**Important:** Since we use `--max-age-days 0`, a re-run immediately after
interruption will re-process all cards (including already-completed ones).
To avoid re-processing, wait until the next day or use a short age window:

```bash
# Resume after interruption (skip cards priced in the last hour)
# There is no --max-age-hours flag, so the minimum is 1 day.
# Alternative: note the last processed card and use --limit to skip ahead.
python -m src.cli.main liga-sweep --max-age-days 1
```

### If rate limited

Liga may throttle requests. Signs: HTTP 429 responses, empty price results,
or slower-than-usual page loads. The provider has built-in backoff, but if
it persists:

```bash
# Increase delay between cards to 8 seconds
python -m src.cli.main liga-sweep --max-age-days 0 --delay 8

# Or reduce batch size and increase pause
python -m src.cli.main liga-sweep --max-age-days 0 --batch-size 10 --batch-pause 120
```

---

## Step 3 -- Re-export Liga Collection (optional)

If you want fresh Liga buy prices to compare against (e.g., prices changed
since the HTML files were saved), re-export from Liga's website:

1. Log into [Liga Magic](https://www.ligamagic.com.br/)
2. Navigate to your collection view
3. For each page of the collection, press **Ctrl+S** and save as
   "Webpage, Complete" (`.html`) into `docs/htmlsColecao/`
4. Replace the existing 7 files, or add new ones (the script reads all
   `.html` files in the directory)

If you do NOT re-export, the comparison will use the existing HTML files.
This is fine for measuring the sweep fix impact, since we are comparing
our new prices against the same baseline.

---

## Step 4 -- Run Enhanced Comparison

After the sweep completes, run the comparison script:

```bash
python scripts/liga_collection_compare.py
```

### Output files

| File | Description |
|------|-------------|
| `scripts/debug_output/collection_data.json` | Raw parsed cards from Liga HTML |
| `scripts/debug_output/price_comparison.csv` | Full comparison report (all cards) |
| `scripts/debug_output/mismatches.csv` | Only cards with >20% difference |

### Console output

The script prints a structured summary:

1. **Status counts** -- how many cards fall into each bucket
2. **Price type note** -- reminder that Liga shows "lowest buy" vs our "mid"
3. **Root-cause hint breakdown** -- classification of mismatches by likely cause
4. **Biggest mismatches** -- top 20 cards with >50% difference
5. **Moderate mismatches** -- top 20 cards with 20-50% difference

### Status definitions

| Status | Meaning | Expected? |
|--------|---------|-----------|
| `OK` | Difference < 5% | Yes -- prices match |
| `DRIFT` | Difference 5-20% | Yes -- normal mid-vs-buy spread |
| `MISMATCH_ABOVE` | 20-50%, our price higher | Usually expected (mid > lowest buy) |
| `MISMATCH_BELOW` | 20-50%, our price lower | Suspicious -- investigate |
| `BIG_ABOVE` | >50%, our price higher | Check hint -- may be expected or wrong edition |
| `BIG_BELOW` | >50%, our price lower | Bug -- our price should never be below Liga's lowest buy |
| `NO_OUR_PRICE` | Card in collection but no Liga price stored | Sweep may have failed for this card |
| `NO_LIGA_PRICE` | Card in our DB but Liga HTML has no price | Liga may not list a buy price |
| `NOT_IN_DB` | Card in Liga HTML but not found in our DB | Matching issue (diacritics, name mismatch) |

### Root-cause hint definitions

| Hint | Meaning |
|------|---------|
| `foil_card` | Card has "Foil" in extras -- foil/non-foil price confusion |
| `dfc_card` | Double-face card (name contains " // ") -- URL or edition issue |
| `art_card` | Art Series or Art Card -- typically no market price |
| `promo` | Promo or Pre-Release printing -- variant pricing |
| `variant_ed` | Variant edition (Borderless, Showcase, Extended Art, Retro) |
| `cheap_card` | Liga buy price < R$1.00 -- noise, even small diffs show high % |
| `expected` | Positive diff, no other hint, Liga > R$5 -- normal mid-vs-buy |
| (empty) | No hint applies -- needs manual investigation |

---

## Step 5 -- Classify Results

Review the summary output and apply these rules:

### Green flags (no action needed)

- **`OK` + `DRIFT` count** should represent >80% of total cards
- **`BIG_ABOVE` with hint=`expected`** are fine (mid naturally exceeds
  lowest buy for cards above R$5)
- **`BIG_ABOVE` with hint=`cheap_card`** are noise (sub-R$1 cards where
  R$0.50 difference shows as 200%)
- **`MISMATCH_ABOVE` with hint=`expected`** are acceptable spread

### Yellow flags (investigate, may need fixes)

- **`BIG_ABOVE` with hint=`foil_card`** -- foil price stored for non-foil
  card, or vice versa. If significant count, T06 is needed.
- **`BIG_ABOVE` with hint=`dfc_card`** -- double-face card URL or edition
  mismatch. If significant count, T05 is needed.
- **`BIG_ABOVE` with hint=`variant_ed`** -- variant edition price picked
  instead of standard printing. May need T04 sigla mapping.
- **`MISMATCH_BELOW`** -- our mid is lower than Liga's lowest buy by
  20-50%. Could be stale data or wrong edition.

### Red flags (bugs requiring fixes)

- **`BIG_BELOW` count should be 0** -- our mid price must never be below
  Liga's lowest buy price. Any BIG_BELOW entries are genuine bugs.
- **`NOT_IN_DB` count should be 0** -- the diacritics fix (T01) should
  resolve all name-matching failures. If any remain, the comparison
  script needs further matching improvements.
- **`NO_OUR_PRICE`** in large numbers -- sweep failures need investigation.

---

## Step 6 -- Investigate Specific Mismatches

For individual cards that need deeper analysis, use the debug script.

### Single card

```bash
python scripts/liga_debug.py "Card Name"
```

With edition selection (collector number and set code):

```bash
python scripts/liga_debug.py "Card Name" --collector-number 123 --set-code fdn
```

To see the browser window (non-headless, useful for debugging):

```bash
python scripts/liga_debug.py "Card Name" -cn 123 -sc fdn --no-headless
```

### Batch investigation

Process the top mismatches from the comparison output:

```bash
# Investigate top 20 mismatches
python scripts/liga_debug.py --batch scripts/debug_output/mismatches.csv --limit 20

# Investigate all mismatches (slow -- 5s per card)
python scripts/liga_debug.py --batch scripts/debug_output/mismatches.csv
```

### Debug output (single card mode)

| File | Description |
|------|-------------|
| `scripts/debug_output/screenshot.png` | Full page screenshot |
| `scripts/debug_output/screenshot_price.png` | Price area screenshot |
| `scripts/debug_output/prices.html` | Extracted price-relevant HTML sections |
| `scripts/debug_output/full_page.html` | Complete page HTML |
| `scripts/debug_output/parsed.json` | What our parser extracted |

### Debug output (batch mode)

| File | Description |
|------|-------------|
| `scripts/debug_output/batch_debug.csv` | Summary CSV with liga_mid, edition_matched, diff_pct |

---

## Step 7 -- Decide Wave 2 Scope

Based on the classification from Step 5, determine which Wave 2 tasks are
needed:

| Condition | Decision |
|-----------|----------|
| >80% of cards are OK + DRIFT | Wave 2 may be minimal or skipped entirely |
| Significant `foil_card` mismatches | T06 needed (foil edition fallback) |
| Significant `dfc_card` mismatches | T05 needed (double-face card handling) |
| Sigla mismatches identified (Scryfall set_code != Liga sigla) | T04 needed (set code normalization) |
| All clean | Skip to T07 (final validation report) |

### Decision matrix

```
IF BIG_BELOW == 0
   AND (OK + DRIFT) / total > 0.80
   AND NOT_IN_DB == 0
THEN
   Wave 2 is minimal -- proceed directly to T07 validation.

IF BIG_BELOW > 0
   OR (OK + DRIFT) / total < 0.80
THEN
   Identify root causes from hint breakdown.
   Enable T04/T05/T06 as needed.
   Re-sweep after fixes, then T07.
```

---

## Expected Post-Fix Outcomes

Based on analysis of the pre-fix data, the data-sigla fix (commit `1686d03`)
should resolve:

### Should be fixed

- All cases where the wrong edition was selected due to ambiguous
  `collector_number` (e.g., Sol Ring, Orb of Dragonkind, Inferno of
  Star Mounts -- cards printed in many sets sharing collector numbers)
- Cases where a rare/expensive variant was selected instead of the
  standard printing, because the edition dropdown had multiple matches
  for the same collector number

### Will likely remain after the fix

- **Expected mid-vs-buy difference** -- Cards where our mid is naturally
  50-100% above Liga's lowest buy. This is structurally expected and not
  a bug. The "lowest buy" on Liga is the cheapest listing, while our mid
  is the market median.

- **Cheap card noise** -- Cards under R$1.00 where even a R$0.50
  difference shows as 200%+. These are statistical noise, not pricing
  bugs.

- **Wrong edition where sigla does not match** -- If Scryfall's `set_code`
  differs from Liga's `data-sigla` attribute for any set, the
  disambiguation fix will not help. These would need T04 (set code
  normalization mapping).

- **DFC cards with URL issues** -- If the front-face name search on Liga
  returns a different card entirely, or if the edition list does not
  contain the expected printing. These would need T05.

- **Foil/non-foil confusion** -- If a foil price is stored for a non-foil
  entry (or vice versa), the comparison will show a large deviation.
  These would need T06.

---

## Acceptance Criteria Checklist

After completing the procedure, verify these criteria:

- [ ] >80% of cards are OK or DRIFT (within 20% difference)
- [ ] 0 cards where our price < Liga's lowest buy (`BIG_BELOW` count is 0)
- [ ] No card with >10x deviation unless documented as a known exception
  (art cards, promos, variant editions with `variant_ed` hint)
- [ ] `NOT_IN_DB` count is 0 (diacritics fix is working)
- [ ] Results recorded in `tasks/features/F129-liga-price-accuracy/F129-T03.md`
  as a post-analysis update

---

## Quick Reference

```bash
# 1. Dry run -- check eligible card count
python -m src.cli.main liga-sweep --max-age-days 0 --dry-run

# 2. Full sweep -- force all cards through fixed code
python -m src.cli.main liga-sweep --max-age-days 0

# 3. Compare -- generate reports
python scripts/liga_collection_compare.py

# 4. Debug a single card
python scripts/liga_debug.py "Sol Ring" -cn 367 -sc cmm

# 5. Debug batch of mismatches
python scripts/liga_debug.py --batch scripts/debug_output/mismatches.csv --limit 20
```

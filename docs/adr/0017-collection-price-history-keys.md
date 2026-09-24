# ADR 0017 — Collection price history: per-variant key contract, priority merge, honest snapshots

**Status:** Accepted · **Date:** 2026-09-24 · **Feature:** F176

## Context

The price chart on `/collection/:id` stayed empty, or showed only 1–2 points,
for most collection cards. Four earlier features each fixed part of the
problem, but none lined up the history *keys* that writers use with the
keys that readers use:

- **F33** added price history and **F34** added history metrics. Both read
  only the series listed in `source_cards`.
- **F112** added the portfolio history backfill (the portfolio aggregate,
  not the per-card series).
- **F168** added `daily_snapshot` and `backfill_snapshots`. The collection
  endpoint never reads these, and nothing runs them on a schedule.

Writers and readers disagree:

| Writer | `source` | `external_id` | Has a `source_cards` row? |
|---|---|---|---|
| Liga sweep (`liga_sweep.py`), Liga refresh (`collection.py`), scan (`scan.py`) | `liga` | `liga_{card_id}` / `liga_{card_id}_foil` | **no** |
| Catalog seeder (`catalog/seeder.py`) | `liga` | `liga_catalog_{set}_{num}` | yes |
| MYP (`snapshot_prices.py`) | `myp`, `jsonld_snapshot` | `myp_{id}` | yes |
| Manual price entry (F50) | `manual` | `manual_{card_id}` | no |
| `run_daily_snapshot` / `backfill_snapshots` (F168) | `daily_snapshot` | the `external_id` of the latest observation | inherits |

`GET /collection/{id}/history` and `/{entry_id}/metrics` loop over
`source_cards` and filter on `source IN (sc.source, 'jsonld_snapshot')`.
Because of that, the main source (Liga `mid`) is never read.

### Diagnosis (F176-T01, `tasks/features/F176-collection-price-history/diagnosis.md`)

The numbers below come from a fixture built with the real write paths
(`insert_price_observations`, `backfill_snapshots`, `run_daily_snapshot`).
The same numbers came out on SQLite and on a throwaway PostgreSQL 16. The
fixture has 4 entries in a 30-day window: normal Liga, foil Liga, MYP with
`source_cards`, and one unlinked entry. The local DB was empty and Neon was
unreachable, so **production numbers are still pending**: the user must
run `scripts/diagnose_collection_history_neon.sql` (Governance amendment 3,
AC15).

| # | Hypothesis | Status | Evidence (fixture numbers) |
|---|---|---|---|
| H1 | The endpoint reads only `source_cards`, so `liga_{id}[_foil]` is invisible | **Confirmed** | All 14 `liga` points lost (14/14). Entries 1 and 2 return `endpt=0` although 12 and 20 points exist. **75%** of entries get 0 points from the current endpoint. |
| H2 | Filter `[sc.source, 'jsonld_snapshot']` drops `daily_snapshot` and `manual` | **Confirmed** | All 35 `daily_snapshot` rows lost (35/35). The MYP entry with `source_cards` loses 14 snapshots and returns only 3 points. |
| H3 | Nothing schedules `daily-snapshot`; the sweep revisits a card ≤1×/week | **Confirmed (code) / inconclusive (real data)** | 4–5 real days out of 30. `bats/` contains only `fetch-news.bat` and `process-queue.bat`. `liga-sweep` registers only the alert hook (`main.py` L1181). `--max-age-days` defaults to 7. |
| H4 | Foil and normal series are mixed | **Confirmed** | Foil entry 2 has 11 `liga_2_foil` rows and 9 `liga_2` rows, with 9 dates carrying more than one point. The old backfill also fabricated `daily_snapshot` rows for **both** variants. |
| H5 | Several points on the same day, no dedup | **Confirmed** | `duplicate_dates` = 1 / 9 / 7 for entries 1 / 2 / 3. There are up to 5 observations on one day (card 3, d-3: liga + myp + jsonld + 2× daily_snapshot). |
| H6 | `backfill_snapshots(days>1)` fabricates a flat history from the current price | **Confirmed** | 30 of the 35 `daily_snapshot` rows are retroactive (`observed_at < date(created_at)`), with 7 consecutive identical prices per series. |

With the resolver defined below replicated inline, linked entries go from
0 / 0 / 3 days to **11 / 10 / 10 days**. Entries with ≥2 days go from 25%
to **75%**, and all foil/normal mixing disappears.

Precedent: F175 (`src/database/trending_queries.py`, `parse_direct_card_id`)
already fixed H1 for market trending. It combines `source_cards` with the
direct `liga_{id}` and `manual_{id}` keys and excludes `_foil`. That is
the same normal-variant rule adopted here.

**Root cause:** there is no single contract that says which
`(source, external_id)` series belong to a collection entry. Each reader
re-derives the answer from `source_cards`, which the main writer (the Liga
sweep) never populates. That is a **key contract** problem, not a data
problem. The fix belongs on the read side, plus reliable daily writes.

## Decision

### 1. One pure resolver owns the key contract

`src/collection/price_history_keys.resolve_history_keys(card_id, source_cards, is_foil)`
has no database access. It is the **only** place that decides which series
make up a card's history. Every history reader must use it:
`/collection/{id}/history`, `/collection/{id}/metrics` and
`/cards/{id}/history`. They reach it through
`src/services/collection_price_history.build_history`, which runs one
`external_id IN (…)` query. Rows from different variants cannot collide,
because the unique key is `(source, external_id, observed_at)`.

The variant comes from `is_foil_entry(UserCollectionRow.extras)`.
`/cards/{id}/history` has no collection entry, so it uses the normal
variant.

| Variant | Keys (in this order, no duplicates) | Excluded |
|---|---|---|
| **normal** | `('liga', 'liga_{id}')`, `('daily_snapshot', 'liga_{id}')`; `('manual', 'manual_{id}')`, `('daily_snapshot', 'manual_{id}')`; for each non-foil `source_card (s, e)`: `(s, e)`, `('jsonld_snapshot', e)`, `('daily_snapshot', e)`. This covers MYP and `liga_catalog_{set}_{num}`. | every `*_foil` key |
| **foil** | `('liga', 'liga_{id}_foil')`, `('daily_snapshot', 'liga_{id}_foil')`; `('manual', 'manual_{id}')`, `('daily_snapshot', 'manual_{id}')`; `source_cards` whose `external_id` ends in `_foil`, plus `jsonld_snapshot` and `daily_snapshot` for each | `liga_{id}` **and its `daily_snapshot`**, and every non-foil `source_card` (including MYP, which has no foil key) |

`card_id ≤ 0` raises `ValueError`. Snapshot keys are listed explicitly
per variant. This matters because `backfill_snapshots` partitions by
`external_id`, so an old, isolated `liga_{id}` row could otherwise leak
fabricated points into a foil chart (diagnosis finding 2).

### 2. At most one point per day, chosen by source priority

`merge_series_by_priority` groups observations by `observed_at` and skips
`median_price is None`. On each day it keeps the observation with the
lowest priority value:

| Priority | Source |
|---|---|
| 0 | `manual` |
| 1 | `liga` |
| 2 | `jsonld_snapshot` |
| 3 | `myp` |
| 5 | unknown source |
| 9 | `daily_snapshot` (carry-forward, always last) |

In words: **`manual > liga > jsonld_snapshot > myp > daily_snapshot`**.
When two observations tie on priority, the lexicographically smaller
`external_id` wins, so the result is deterministic. Output is sorted
ascending by date. `SOURCE_PRIORITY` stays aligned with
`Repository.SOURCE_PRIORITY`, which does not list `daily_snapshot`, so the
resolver module holds the extended copy.

The response gains an optional `meta` (`PriceHistoryMeta`) field:
`variant`, `sources`, `first_observed_at` (first *real* observation),
`last_observed_at`, `real_points` (source ≠ `daily_snapshot`) and
`snapshot_points`. `PriceObservation.source` is filled with the winning
source for each day. Both fields are additive and backward-compatible.

### 3. Bounded carry-forward (`MAX_CARRY_FORWARD_DAYS = 30`)

`run_daily_snapshot` copies an `external_id` forward only while its last
*real* observation (source ≠ `daily_snapshot`) is at most 30 days old.
Abandoned cards stop growing a flat line forever. Signature
`run_daily_snapshot(repo) -> int` is preserved (admin router, CLI).

### 4. Honest backfill (forward-fill from real observations)

`backfill_snapshots(repo, days, dry_run=False)` fills day `d` only when all
of these hold:

- `first_real_date ≤ d ≤ today`
- `d` has no observation for that `external_id`
- the last real observation ≤ `d` is ≤ 30 days old

It uses the **price of that last real observation**, not today's price.
It never creates a point before the first real observation, and it drops
the old "skip ids that already have a snapshot" shortcut. Idempotence
comes from the unique constraint plus `on_conflict_do_nothing`. `days` is
still capped at 90, and `dry_run` returns the same count without writing.

**Backfill marker (Governance amendment 5).** Forward-filled rows must be
distinguishable from real daily snapshots and deletable on their own. The
marker is a dedicated source value, **`daily_snapshot_backfill`**, written
by `backfill_snapshots`. The resolver and merge treat it exactly like
`daily_snapshot`: the same keys per variant, priority 9, and it does not
count as a "real" point. If F176-T05 ships a different but equivalent
marker, T05 records it under "Notes from Developer" and updates this
paragraph. Real snapshots written by `run_daily_snapshot` keep
`source='daily_snapshot'`.

### 5. The daily write runs automatically after the Liga sweep

`run_liga_sweep(..., snapshot_after=True)` calls `run_daily_snapshot` at
the end of any sweep that is not a dry run and has
`total_processed > 0`. The call is wrapped in `try/except`, only logs on
failure, and never fails the sweep. This is the **primary** mechanism,
because the production path is `push-all.bat → liga-sweep` (that file is
not in this repo). `bats/daily-snapshot.bat` is only a manual/backfill
fallback for days without a sweep. There is no in-process scheduler on
Render (`src/api/app.py` is out of scope).

### 6. No schema change, no data migration

`src/database/models.py` and the `external_id` formats already stored are
untouched. Existing rows are read as they are.

## Consequences

- Normal cards with only `liga_{id}` rows now get a chart: AC3 requires
  ≥3 points where there were 0 before. Foil entries show only the foil
  series (AC4).
- History, metrics and card history share one resolver and one query
  (`build_history`). Any new history reader must go through it. **Do not**
  re-derive series from `source_cards` again.
- **Old flat snapshots stay in the database.** Rows that the pre-F176
  backfill created carry `source='daily_snapshot'` and cannot be told
  apart by source. They can be found with
  `observed_at < CAST(created_at AS DATE)`, because a real
  `run_daily_snapshot` always writes `observed_at = today`. Priority 9
  means they never override a real point on the same day, but they can
  still draw flat segments. Cleaning them up is **optional**, needs a
  **backup first**, and must **only be run with the user's explicit
  approval** (CLAUDE.md: never `DELETE` without confirmation). The SQL
  below is a suggestion only and **was not executed**:

  ```sql
  -- NOT EXECUTED — run only with explicit user approval, after a Neon backup/branch.
  -- 1) Inspect first:
  -- SELECT external_id, COUNT(*)
  --   FROM price_observations
  --  WHERE source = 'daily_snapshot'
  --    AND observed_at < CAST(created_at AS DATE)
  --  GROUP BY external_id
  --  ORDER BY 2 DESC;
  --
  -- 2) Optional cleanup of retroactive (fabricated) snapshots from the old backfill:
  -- BEGIN;
  -- DELETE FROM price_observations
  --  WHERE source = 'daily_snapshot'
  --    AND observed_at < CAST(created_at AS DATE);
  -- -- verify the row count, then COMMIT or ROLLBACK
  -- ROLLBACK;
  --
  -- 3) Rows from the new forward-fill can be removed on their own by marker:
  -- DELETE FROM price_observations WHERE source = 'daily_snapshot_backfill';
  ```

- **MYP and foil:** MYP has no `_foil` key in the diagnosis, so foil charts
  never include MYP. Confirm with Q1 on Neon (`other` family with `_foil`).
  If MYP foil keys ever appear in `source_cards`, the foil rule picks them
  up automatically.
- **Follow-up: `low` vs `mid` on the same key** (diagnosis finding 1). The
  Liga sweep writes `mid → low → high`, but collection refresh
  (`collection.py` ~L1496) and scan (`scan.py` ~L72) write
  `low → mid → high` into the same `liga_{id}` key. Whichever write lands
  first each day wins, so the series can alternate between the lowest
  listing and the market price. This is out of scope for F176, which does
  not change the semantics of stored data. Unify the writers to `mid`
  (CLAUDE.md) in a later feature.
- **Follow-up: `get_price_series_batch`** (`repository.py` L880, used by
  `/cards/trends` sparklines and deck valuation) has the same H1 defect:
  it reads only `source_cards` and returns empty for Liga-only cards. Out
  of scope for F176 (`repository.py` is off limits in this batch). A later
  feature should route it through `resolve_history_keys`.
- **F175 interaction:** market trending already excludes `_foil`, which
  matches the normal-variant rule. No change is needed, and T12 must not
  lock in anything beyond that.
- **Known blend:** `get_all_latest_prices` ignores source, so the
  `daily_snapshot/myp_{id}` series can carry forward from `myp` or from
  `jsonld_snapshot`. This is acceptable because it is the same product
  and snapshots always have the lowest priority.
- **Contract adjustments from the diagnosis to shard 02:** none to the key
  rules. Two clarifications apply: `meta.real_points` excludes every
  snapshot source (including `daily_snapshot_backfill`), and the backfill
  marker above.

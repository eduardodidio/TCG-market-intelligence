# Execution Plan: F171–F179 (batch)

**Created:** 2026-09-24
**Target branch:** `homol` (one worktree/branch per feature, merged into `homol`)
**Gandalf decision:** `logs/decisions/D-F171-F179-20260924-001.json` (governance: agree)

## Features Overview

| Feature | Folder | Tasks | Waves | Type | Priority tier |
|---|---|---|---|---|---|
| F171 Collection import currency (BRL vs USD) | `F171-collection-import-currency/` | 14 | 6 | Bugfix | 1 |
| F172 Deck builder fix + "Sugestão de deck" (Claude queue) | `F172-deck-builder-suggestions/` | 18 | 5 | Feature | 3 |
| F173 Metagame top decks by format | `F173-metagame-top-decks/` | 15 | 5 | Feature (spike first) | 3 |
| F174 Trades with the same filters/layout as My Collection | `F174-trades-collection-filters/` | 14 | 4 | UX | 2 |
| F175 Trending in market mode (toggle off) | `F175-trending-market-mode/` | 8 | 3 | Bugfix | 1 |
| F176 Collection price history (definitive fix) | `F176-collection-price-history/` | 12 | 5 | Bugfix | 1 |
| F177 Banlist fill + "Somente minha coleção" + history in card | `F177-banlist-fill-owned-history/` | 10 | 4 | Bugfix + UX | 2 |
| F178 News collection via .bat | `F178-news-collection-bat/` | 8 | 5 | Bugfix | 1 |
| F179 Achievements reward Treasure tokens (50→1000) | `F179-achievement-treasure-rewards/` | 9 | 3 | Feature | 2 |

**Total: 108 tasks across 9 features.** None of them changes `src/database/models.py`.
The new tables (F172 `deck_suggestion_requests`, F173 `meta_decks`/`meta_deck_cards`) live in
their own modules and are created with `checkfirst`.

## Strategy

Every feature isolated its batch-shared "hotspot" files (`README.md`, `src/cli/main.py`,
`src/api/app.py`, `App.tsx`, `Layout.tsx`, `bats/`) in a small last-wave task. That allows two phases:

### Phase A: fully parallel (9 worktrees)

Run every feature's waves **except its integration task(s)** at the same time, one worktree per feature:

```
Worktree F171: W0 → W4          (stop before T13, T14)
Worktree F172: W0 → W3          (stop before T17, T18)
Worktree F173: W0 → W3          (stop before T15)   ⚠ gate after W0, see below
Worktree F174: W0 → W2 + T13    (stop before T14)
Worktree F175: W0 → W1 + T07    (stop before T08)
Worktree F176: W0 → W3 + T12    (stop before T11)
Worktree F177: W0 → W2          (stop before T09, T10)
Worktree F178: W0 → W2 + T08*   (stop before T07)
Worktree F179: W0 → W1 + T08    (stop before T09)
```
\* F178-T08 (live source validation) runs on the user's machine after T07.

Across features, the Phase A file overlaps are limited to **additive** edits:

| File | Touched by (Phase A) | Nature | Resolution |
|---|---|---|---|
| `frontend/src/i18n/locales/{en,pt-BR}.json` | F171-T11, F174-T02, F176-T10, F177-T02, F178-T05, F179-T03 | each adds its own block | trivial JSON merge conflict, keep both blocks |
| `frontend/src/types/api.ts` | F171-T11, F172-T06, F176-T10 | additive fields/types | keep both |
| `src/api/routers/collection.py` | F171-T09/T10 (`batch_*`, `import_collection`), F176-T08 (`get_collection_history`, `get_card_metrics`) | different functions | auto-merge expected |
| `src/api/schemas/collection.py` | F171-T09/T10, F176-T04 | additive classes/fields | auto-merge expected |
| `src/database/repository.py` | F175-T03 (`get_trending_price_data`), F178-T03 (news section) | different sections | auto-merge expected |

**Logical coupling (not a file conflict):** F175 and F176 both hit the Liga `external_id`
join issue (`liga_{card_id}` vs `liga_catalog_{set}_{num}`). F176-T01 diagnosis and ADR 0017
own the key contract. F175-T03 must read `F176-*/diagnosis.md` if it exists at run time and
must not redefine the contract.

### Phase B: serialized integration (hotspots)

Run the integration tasks **one feature at a time**. Before each one, merge the latest `homol` into
the feature branch (merge, no rebase), run the task, validate, and merge into `homol`:

| # | Integration task(s) | Hotspot files |
|---|---|---|
| 1 | F175-T08 | README |
| 2 | F178-T07 | main.py, bats/fetch-news.bat, README |
| 3 | F171-T13, F171-T14 | main.py, README |
| 4 | F176-T11 | main.py, bats/daily-snapshot.bat, README |
| 5 | F179-T09 | main.py, Layout.tsx, README |
| 6 | F177-T09, F177-T10 | App.tsx, Layout.tsx, bats/banlist-sync.bat, README |
| 7 | F174-T14 | README |
| 8 | F172-T17, F172-T18 | app.py, main.py, bats/deck-suggestions.bat, .env.example, i18n, README |
| 9 | F173-T15 | app.py, main.py, i18n, README, .gitignore |

The order follows the priority tiers: data-correctness bugs first, the big features last. Each
integration task is small (a few lines), so Phase B is short even though it runs serially.

## Reserved ADR numbers

These numbers override any "next free number" instruction inside the task files:

| ADR | Feature |
|---|---|
| 0014 | F171 import currency normalization |
| 0015 | F172 deck suggestion queue + Claude |
| 0016 | F173 metagame deck sources |
| 0017 | F176 collection price history keys |
| 0018 | F177 banlist compact legality storage |
| 0019 | F178 news collection offline bat |
| 0020 | F179 achievement reward ledger idempotency |

## Gates and pending user decisions

1. **F173 spike gate:** after F173-W0, the user approves ADR 0016 (source matrix, ToS/robots) before W1.
2. **F172: CONFIRMED by user (2026-09-24):** `claude -p` default, no SDK. Original notes:
   - (a) The `anthropic` SDK is **not** added. The plan uses the Claude CLI (`claude -p`) by default, with an opt-in HTTP API through the existing `httpx`.
   - (b) The default API model is `claude-sonnet-5` (`DECK_SUGGEST_MODEL`).
   - Confirm both before W1.
3. **F171:** attach the friend's real export file to `tests/fixtures/collection_import/` if possible. The plan covers Liga, ManaBox-style and generic exports.
4. **Local routines (post-merge, on the user's Windows machine):** schedule these in Task Scheduler:
   - `bats/fetch-news.bat`
   - `bats/daily-snapshot.bat`
   - `bats/banlist-sync.bat`
   - `bats/deck-suggestions.bat` (daily)
   - `bats/collect-metagame.bat`

## How to run

```
/create-feature F175   # etc. Use one worktree per feature for Phase A, then Phase B in the order above
```

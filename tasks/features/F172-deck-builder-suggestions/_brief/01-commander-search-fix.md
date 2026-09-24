# 01 — Commander search fix + deck-build module review

## Current flow

`DeckBuildWizard.tsx` (step 2, commander formats) → `searchCommanders(q)`
(`frontend/src/api/decks.ts:56`) → `GET /api/v1/decks/commanders?q=` (`src/api/routers/decks.py:243`)
→ `get_commander_candidates()` (`src/decks/builder.py:333`).

`src/api/routers/card_search.py` is the **LigaMagic web search** (`/cards/search-web`, 1 credit).
The wizard does **not** use it and it is **out of scope**. Do not change it.

## Root cause analysis (Architect)

`get_commander_candidates` builds:

```python
select(CardRow).where(
    CardRow.game == "magic",
    CardRow.type_line.isnot(None),
    CardRow.type_line.contains("Legendary"),
    CardRow.type_line.contains("Creature"),
)
.where(CardRow.name_en.ilike(f"%{search}%"))
.where(CardRow.id.in_(select(CardLegalityRow.card_id).where(format=="commander", status=="legal")))
.order_by(CardRow.name_en).limit(limit)
```

| # | Defect | Effect |
|---|--------|--------|
| H1 (primary) | Hard `IN card_legalities` filter. That table is filled only by `banlist-sync` (`src/collectors/banlist_sync.py`), which in per-card mode covers only cards with set/collector and may never have run on the deployment. | **Zero results** whenever legality rows are missing |
| H2 | Only `name_en` is searched. Brazilian users type PT names ("Atraxa, Voz dos Pretores"). | No results for PT queries |
| H3 | No dedupe by name: 20 printings of the same commander fill `limit`. The color post-filter runs **after** `limit`. | Results are truncated or empty with a color filter |
| H4 | Cards created by collection import / MYP parser / batch-add may have `type_line` NULL. | Owned commanders are invisible (acceptable, but document it) |
| H5 (frontend) | `searchCommanders` errors are ignored. There is no "nenhum resultado" state. There is no guard against out-of-order responses (debounced, but an older response can overwrite a newer one). `searchingCommanders` stays `true` if the promise throws. | Silent failure looks like "doesn't find cards" |
| H6 (review) | `_query_candidates()` (`builder.py:155`, same hard legality filter at line ~188) → `generate_deck` produces decks with 0 non-land cards when legalities are missing. | Generated deck = only lands |
| H7 (review) | `generate_deck` declares `prices: dict[int, Decimal] = {}` (`builder.py:449`) and never fills it. The budget limit is never enforced, and `price` / `total_value` are always None. | Budget feature broken |
| H8 (review) | `FORMAT_INFO` in the wizard has no `pioneer` / `vintage`, although `_VALID_FORMATS` (router) accepts them. | The brief explicitly asks for Pioneer |
| H9 (review) | The wizard uses i18n keys `deckBuild.*`, but the locales define `deckBuilder.*`, so the wizard always shows English defaults. | i18n gap (fixed in T18) |

## Required fix (backend, F172-T02)

- Legality becomes a **soft** filter. Exclude a card only if it has an explicit commander legality row with
  status in (`banned`, `not_legal`). Cards **without** a row pass (fallback to the type_line heuristic).
  Use `~CardRow.id.in_(select(... status.in_(["banned","not_legal"])))`.
  Apply the same rule in `_query_candidates` (format = requested format).
- Search `name_en` **OR** `name_pt` (`ilike`, strip whitespace, escape `%`/`_`). Require at least 2 characters after strip,
  otherwise return `[]`.
- Apply the color filter **before** the limit: fetch up to `limit * 10` rows (cap 500), run the Python post-filter,
  dedupe by `name_en.lower()` (prefer a row with `image_uri`, then the most recent `id`), then slice `[:limit]`.
- Order: exact name match first, then prefix match, then alphabetical (Python sort after dedupe).
- Add `name_pt` to the returned dict and to the `CommanderCandidate` schema (`src/api/schemas/decks.py`) as an optional field.
- Add a pure helper `is_commander_eligible(type_line: str | None) -> bool` in `builder.py`.
  Rule: `"Legendary" in tl and "Creature" in tl`, OR `"can be your commander"` handled later (out of scope).
  Use it in `decks.py` `generate_deck_endpoint` (it replaces the inline check) and later in F172-T08.
- Fill `prices` in `generate_deck`: collect candidate ids, then call `repo.get_latest_prices_batch(ids)`
  (`src/database/repository.py:724`). Price = `row.median_price` (skip None). Use it for budget + `price` + `total_value`.

## Required fix (frontend, F172-T06)

Extract `frontend/src/components/decks/CommanderSearch.tsx` (reused by the suggestion form):

```ts
interface CommanderSearchProps {
  selected: CommanderSearchResult | null;
  onSelect: (c: CommanderSearchResult) => void;
  onClear: () => void;
}
```

- Debounce 300 ms, min 2 chars (trimmed). A request-sequence ref ignores stale responses.
- `try/finally` so loading is always reset. Show `resp.errors[0].message` in an inline error.
- Empty state: "Nenhum comandante encontrado para “{q}”" when a search finished with 0 results.
- Show `name_pt` under `name_en` when it is present and different.
- `data-testid`s: keep `commander-search`, `selected-commander`, `commander-option-{id}`. Add `commander-search-empty`,
  `commander-search-error`, `commander-search-loading`.
- `CommanderSearchResult` in `frontend/src/types/api.ts` gets `name_pt?: string | null`.
- Wizard: add `pioneer` (60) and `vintage` (60) to `FORMAT_INFO`.

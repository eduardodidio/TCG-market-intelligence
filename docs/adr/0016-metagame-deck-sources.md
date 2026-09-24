# ADR-0016: Metagame Deck Sources (F173)

## Status
Accepted (2026-09-24) — live ToS/robots verification **pending-user** (see below).
Approval of this ADR is the F173 spike gate before Wave 1.

## Context
F173 adds a "Mercado" tab to Top Decks: the top metagame decks per format
(Commander, Standard, Pioneer, Modern, Legacy, Vintage, Pauper), priced in BRL
with our own price data and with the user's owned %. We need an external
source of decklists and meta rank. Collection runs only locally
(`bats/collect-metagame.bat`, weekly), never from Render.

Rule from the brief: **a source whose ToS forbids automated collection, or
whose robots.txt disallows the URLs we need, is dropped**, even if the data is
good. Tie-breakers: fewer requests per collection, structured data
(JSON/text) over HTML, having a meta share.

### Live verification: pending-user
The spike ran on 2026-09-24 in the cloud sandbox. The egress proxy refused
every request to the candidate hosts:

- `curl` → `CONNECT tunnel failed, response 403` for `edhrec.com`,
  `json.edhrec.com`, `www.mtgtop8.com`, `www.mtggoldfish.com`, `mtgdecks.net`.
- WebFetch → "proxy refused the connection" for the same `robots.txt` URLs.
- WebSearch worked. It confirmed the EDHREC ToS URL
  (`https://edhrec.com/terms`, Space Cow Media) and that `json.edhrec.com`
  is a public JSON endpoint that needs no key. It returned no robots.txt contents.

The matrix below is therefore based on documented knowledge of these sites,
not on a fresh capture. **Before the first real collection, the user must
open the URLs in the "To verify" column from a normal network**
and confirm them. If any check fails, the fallback in *Consequences* applies.
The fixtures are **synthetic** (see `tests/fixtures/metagame/README.md`)
and must be revalidated on the first real run.

## Source matrix

| Source | ToS (URL, checked 2026-09-24) | robots.txt (URL, checked 2026-09-24) | Data format | Fields | Requests / collection | Risk | Verdict |
|---|---|---|---|---|---|---|---|
| **EDHREC** | `https://edhrec.com/terms`. It is a general-use ToS. As far as we know it has no clause against low-rate automated reads of the public JSON. To verify: no "scrape/crawl/automated" ban. | `https://json.edhrec.com/robots.txt` and `https://edhrec.com/robots.txt`. To verify: `/pages/` is not disallowed for `*`. | JSON (`json.edhrec.com/pages/...`) | rank (list order), commander name, slug, `num_decks`, color identity, average-deck card list (100 cards) | 1 + N (N = limit) | Low. The JSON is not an official API, so its shape can change. | **Chosen: Commander** |
| **MTGTop8** | `https://www.mtgtop8.com/` has no restrictive ToS page that we know of. To verify: the site footer has no terms link. | `https://www.mtgtop8.com/robots.txt`. To verify: `/format`, `/archetype` and `/mtgo` are allowed for `*`. Honor `Crawl-delay` if present. | HTML (meta pages) + plain-text MTGO export | archetype, meta share %, archetype id, deck id, player, event, finish, date, full main + side decklist | 1 + 2N per format | Medium. The HTML scraping is fragile. | **Chosen: constructed** (Standard, Pioneer, Modern, Legacy, Vintage, Pauper) |
| MTGGoldfish | `https://www.mtggoldfish.com/terms`. As far as we know, the ToS forbids automated scraping/crawling without written permission. | `https://www.mtggoldfish.com/robots.txt` | HTML (`/metagame/<fmt>/full`) + text export | archetype, meta %, decklist, prices (USD) | 1 + N | High (ToS). Also has anti-bot protection. | **Dropped** (ToS) |
| mtgdecks.net | `https://mtgdecks.net/terms`. As far as we know it restricts automated extraction, and it sits behind Cloudflare bot protection. | `https://mtgdecks.net/robots.txt` | HTML | archetype, meta %, decklist | 1 + N | High (ToS + anti-bot) | **Dropped** |
| Moxfield / Archidekt (optional) | `https://moxfield.com/terms`, `https://archidekt.com/terms`. They offer an unofficial API that needs permission/UA agreement. | n/a (API) | JSON | user decks, no meta rank | many | High. The API is unofficial and needs explicit permission. | **Not used** (no meta rank, and no permission) |

Edge cases from the spike:
- **Commander has no tournament meta share.** For Commander, `meta_share_pct = None`
  and `rank` is set by popularity (`deck_count` = EDHREC `num_decks`, in list order).
- **Formats with no valid source:** none. All 7 formats are covered. If a later
  verification drops MTGTop8 for a format, that format is marked **"não suportado"**
  here and T08/T12 leave it out of `SOURCE_FOR_FORMAT`.

## Decision

### Source per format (`SOURCE_FOR_FORMAT`, populated by T12)

| Format | Source | Source code | Rank basis |
|---|---|---|---|
| commander | `edhrec` | — | popularity (`num_decks`), `meta_share_pct = None` |
| standard | `mtgtop8` | `ST` | meta share % |
| pioneer | `mtgtop8` | `PI` | meta share % |
| modern | `mtgtop8` | `MO` | meta share % |
| legacy | `mtgtop8` | `LE` | meta share % |
| vintage | `mtgtop8` | `VI` | meta share % |
| pauper | `mtgtop8` | `PAU` | meta share % |

```python
SOURCE_FOR_FORMAT = {
    "commander": "edhrec",
    "standard": "mtgtop8", "pioneer": "mtgtop8", "modern": "mtgtop8",
    "legacy": "mtgtop8", "vintage": "mtgtop8", "pauper": "mtgtop8",
}
```

The constructed source is still MTGTop8, as the plan assumed. T08 keeps
`src/metagame/sources/mtgtop8.py` / `Mtgtop8Source`, so no plan files change.

### Exact URLs used by the adapters

**EDHREC (`EdhrecSource`, T07)**
1. Top list: `https://json.edhrec.com/pages/commanders/year.json`.
   Entries: `container.json_dict.cardlists[*].cardviews[*]`, with `name`, `sanitized`
   (slug → `external_id`), `num_decks` (→ `deck_count`), `color_identity`
   (→ `colors`). Rank is the list position. Skip an entry that has no `name`
   or `sanitized` and log a warning.
2. Decklist: `https://json.edhrec.com/pages/average-decks/<sanitized>.json`.
   `deck[]` holds `"<qty> <name>"` strings. The line whose name equals the
   commander gets `board="commander"`; all other lines get `board="main"`.
   Keep `//` in split-card names. `source_url` for the UI is
   `https://edhrec.com/average-decks/<sanitized>`.

**MTGTop8 (`Mtgtop8Source`, T08)**
1. Meta page: `https://www.mtgtop8.com/format?f=<CODE>`. Parse the rows
   `tr.hover_tr` that contain `a[href^="archetype?a="]`. These give the
   archetype name, the archetype id (`a=` → `external_id`, which stays stable
   for rank history) and the meta share cell (`"18 %"`, `"9,5 %"` →
   `Decimal`; an empty cell → `None`). Rows without an `archetype?` link,
   such as events, are ignored. Rank is the order by meta share, descending.
2. Archetype page: `https://www.mtgtop8.com/archetype?a=<id>&meta=<meta>&f=<CODE>`
   (use the `href` from step 1). The **representative deck is the first deck
   row**, which is the most recent top finish. Parse `d=<deck_id>` from its link,
   and read `event_date` from the last cell (`dd/mm/yy`).
3. Decklist: `https://www.mtgtop8.com/mtgo?d=<deck_id>`. This is a plain-text
   MTGO export. Main lines come before a line equal to `Sideboard`, and side
   lines (`board="side"`) come after it. `src/decks/parser.py::parse_deck_text`
   parses each `<qty> <name>` line. It does **not** handle the `Sideboard`
   header, so split the text on that line first, then parse each half.
   `source_url` for the UI is `https://www.mtgtop8.com/event?e=<e>&d=<d>&f=<CODE>`.

### Collection policy (implemented by `PoliteFetcher`, T04)
- User-Agent that names us:
  `TEDHC-Market/1.0 (+https://github.com/eduardodidio/TCG-market-intelligence)`.
- robots.txt is checked per host before every request. A disallowed URL raises
  `RobotsDisallowed` and is never fetched.
- At least **3 s between requests to the same host**, or the `Crawl-delay`
  value if it is larger.
- Disk cache: **24 h** for meta/list pages (`commanders/year.json`,
  `format?f=`, `archetype?`) and **7 days** for decklists (`average-decks/*`,
  `mtgo?d=`).
- Retry only on 429, 5xx and timeouts: 3 attempts with exponential backoff,
  honoring `Retry-After`.
- Frequency is **weekly** (Task Scheduler, Monday 06:00), with daily as an
  option. Collection runs only locally, never from the API or Render.
- With the default `limit=20`, a full weekly run is about 21 requests to EDHREC
  plus 6 × 41 = 246 to MTGTop8. At 3 s per host, that takes about 13 min,
  and the cache makes most same-week reruns free.
- **Attribution:** every meta deck in the UI shows "Fonte: EDHREC" or
  "Fonte: MTGTop8" with a link to `source_url`.

### Fixtures (synthetic, revalidate on the first real run)
- `tests/fixtures/metagame/edhrec/top_commanders.json`
- `tests/fixtures/metagame/edhrec/decklist_atraxa-praetors-voice.json`
- `tests/fixtures/metagame/edhrec/decklist_krenko-mob-boss.json`
- `tests/fixtures/metagame/mtgtop8/format_MO.html`
- `tests/fixtures/metagame/mtgtop8/archetype_MO_1452.html`
- `tests/fixtures/metagame/mtgtop8/decklist_boros-energy.txt`
- `tests/fixtures/metagame/mtgtop8/decklist_ruby-storm.txt`

Each folder has a `README.md` with the origin URL and capture date.

## Consequences
- **Fragile scraping.** MTGTop8 HTML and EDHREC's unofficial JSON can change
  without notice. T07/T08 keep their selectors and keys in constants at the top
  of the module. A parse failure skips that deck with a structlog warning
  (lesson F11) and never aborts the format. `CollectStats.errors` shows the
  problem in the CLI output.
- **Plan B:**
  - If MTGTop8 breaks for good or disallows it: mark the constructed formats
    as "não suportado" (remove them from `SOURCE_FOR_FORMAT`). The UI then shows
    an empty state for those formats. Asking MTGGoldfish for written permission
    is the only other candidate.
  - If EDHREC blocks `/pages/`: Commander becomes "não suportado". MTGTop8
    `f=EDH`/`cEDH` is the fallback, which gives duel/cEDH lists rather than
    casual popularity.
- **Pending-user verification.** The ToS and robots cells marked "To verify"
  must be confirmed by the user from a normal network before the first
  `collect-metagame` run. The fixtures must then be replaced by real captures
  trimmed to ≤ 200 KB.
- Commander ranks and constructed ranks mean different things (popularity vs.
  meta share). The API and UI must label them differently
  (`deck_count` vs `meta_share_pct`).
- `data/cache/metagame/` must never be committed (T15 adds it to `.gitignore`).

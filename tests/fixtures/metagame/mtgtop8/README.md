# MTGTop8 fixtures

- **Capture date:** 2026-09-24
- **Status:** synthetic (hand-built, network blocked in sandbox) — revalidate on
  the first real collection and replace with the real page trimmed to ≤ 200 KB
  (strip `<script>`, ads and navigation).

| File | Origin URL | Notes |
|---|---|---|
| `format_MO.html` | `https://www.mtgtop8.com/format?f=MO` | Archetype rows = `tr.hover_tr` with `a[href^="archetype?a="]` + meta share cell (`"18 %"`, `"9,5 %"`, `"7.5 %"`, and one **empty** share → `None`). Also contains an events table whose rows have no `archetype?` link (must be ignored). |
| `archetype_MO_1452.html` | `https://www.mtgtop8.com/archetype?a=1452&meta=44&f=MO` | Deck rows: link `event?e=<event>&d=<deck>&f=MO`, player, event, rank, date `dd/mm/yy`. Representative deck = first row (most recent top finish). |
| `decklist_boros-energy.txt` | `https://www.mtgtop8.com/mtgo?d=712345` | MTGO text export: `<qty> <name>` lines, blank line, `Sideboard`, side lines. 60 main + 15 side. |
| `decklist_ruby-storm.txt` | `https://www.mtgtop8.com/mtgo?d=<deck_id>` | Same shape; includes a `1x Card` line (edge case). 60 + 15. |

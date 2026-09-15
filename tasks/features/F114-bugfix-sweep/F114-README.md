# F114 — Bugfix Sweep (Links + Card Art + Dashboard)

**Status:** planned
**Created:** 2026-09-09
**Branch:** homol

## Summary

Three independent bugfixes: (1) card links abrindo carta errada + Liga URL
sem encoding, (2) artes faltando no catalogo por DFC sem card_faces fallback,
(3) dashboard mostrando "importe sua colecao" mesmo com colecao existente.

## Wave Plan

| Wave | Tasks | Parallelism | Notes |
|------|-------|-------------|-------|
| 0 | T01, T02, T03 | 3 parallel | Zero file overlap entre tasks |

## Task List

| Task | Summary | Wave | Files |
|------|---------|------|-------|
| T01 | Liga URL encoding + CardTile link fix | 0 | collection.py:1638, CardTile.tsx, CollectionCardDetail.tsx |
| T02 | Scryfall DFC image_uri fallback (card_faces) | 0 | scryfall.py:217 |
| T03 | Dashboard collection summary resilience | 0 | Dashboard.tsx |

## File Conflict Map

- **collection.py** — T01 only (Liga URL line ~1638)
- **CardTile.tsx** — T01 only (link target)
- **scryfall.py** — T02 only (_parse_card function)
- **Dashboard.tsx** — T03 only (summaryData guard)
- **Zero overlap between tasks**

## Cross-Feature Parallelism

F114 can run **fully parallel** with F115 (sort) — different file sets.
F114-T01 touches CardTile.tsx which F116 (3D tilt) also touches — merge
F114 before starting F116, or resolve trivially at merge time.

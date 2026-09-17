# F131 — Catalog UX Evolution

## Description

Bring the catalog page to parity with the collection page in
interactivity. The catalog is currently read-only with a fixed grid and
no price-refresh capabilities. This feature adds: grid size toggle
(sm/md/lg), per-card Liga refresh buttons, bulk "Refresh All Set"
button with a new backend endpoint, a search coherence review, and a
comprehensive Final Fantasy set scan.

## Goal

Make the catalog a first-class browsing experience where users can
resize the grid, trigger individual or bulk Liga price refreshes, and
search reliably across both English and Portuguese card names.
Additionally, seed and scan the Final Fantasy Universes Beyond sets so
they appear with prices in the catalog.

## Status: planned

## Waves

| Wave | Tasks | Rationale |
|------|-------|-----------|
| 0 | T01, T02, T04 | All independent. T01 is frontend-only (grid toggle). T02 is frontend-only (reuses existing `POST /api/v1/cards/{card_id}/refresh-price`). T04 is a search coherence review touching frontend + backend query logic. No output dependencies between them. |
| 1 | T03, T05 | T03 needs a new backend endpoint (`POST /api/v1/catalog/scan`) + frontend integration. T05 needs Scryfall set code research, catalog seed, and scan execution. Both are independent of each other but heavier than Wave 0 tasks. |

## Task List

| Task | Title | Wave | Status |
|------|-------|------|--------|
| F131-T01 | Grid Size Toggle on Catalog Page | 0 | planned |
| F131-T02 | Per-Card Liga Refresh Button on Catalog Tiles | 0 | planned |
| F131-T03 | Refresh All Set — Backend Endpoint + Frontend | 1 | planned |
| F131-T04 | Catalog Search Coherence Review | 0 | planned |
| F131-T05 | Final Fantasy Set Scan | 1 | planned |

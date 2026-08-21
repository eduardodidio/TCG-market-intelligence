# Feature F16 — Explore Cards: Sorting Fields

**Status:** planned
**Owner:** @architect
**PRD:** [`docs/prd/F16-explore-cards-sorting.md`](../../../docs/prd/F16-explore-cards-sorting.md)

## Goal

Add sorting controls to the My Collection page so users can order the
card grid by name, set, card number, date added, or price.

## Architecture impact

- **Backend (repository):** `list_collection` and `count_collection` gain
  `sort_by` / `sort_dir` params. Pagination switches from cursor-based
  (`after_id`) to offset-based for this endpoint.
- **Backend (API):** `GET /collection` gains `sort_by`, `sort_dir`, and
  `offset` query parameters.
- **Frontend:** New `SortSelect` component. `MyCollection` page integrates
  sort state, URL params, and client-side price sorting.

## Waves

- **Wave 1**: F16-T01, F16-T02   (backend: repo + API changes)
- **Wave 2**: F16-T03, F16-T04   (frontend: sort component + page integration)
- **Wave 3**: F16-T05            (tests + documentation)

## Global acceptance criteria

- [ ] All sort fields work correctly (name, set, number, added, price)
- [ ] Pagination works with all sort options
- [ ] Sort state is reflected in URL search params
- [ ] Existing tests pass, new tests cover sort logic
- [ ] Backend coverage stays above 70%
- [ ] README.md updated

## Diagrams

- No new diagrams required (UI-only change within existing architecture)
- Update `docs/diagrams/F10-architecture.mmd` if it references the
  collection endpoint query flow

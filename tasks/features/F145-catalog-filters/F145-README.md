# Feature F145 — Catalog Page Filters (Collection-Style Filtering)

**Status:** planned
**Owner:** @architect
**PRD:** (inline — see context in feature request)

## Goal

Upgrade CatalogPage filters to match MyCollection's visual style: replace
the plain `<select>` set dropdown with `SetIconFilter` (scrollable icon
buttons), replace the dual sort selects with the reusable `SortSelect`
component, add an "Owned" toggle filter, and add `rarity`/`collector_number`
sort options to the backend enum so catalog sorting reaches parity with
collection.

## Architecture impact

- **Frontend** — `CatalogPage.tsx` filter bar refactored; new
  `CATALOG_SORT_OPTIONS` constant added to `SortSelect.tsx`.
- **Backend** — `SortByEnum` in `catalog.py` extended with `rarity` and
  `collector_number` values; corresponding SQL sort columns added.
- No new tables, no new endpoints, no new dependencies.

## Waves

- **Wave 0**: F145-T01            (backend: extend catalog sort enum)
- **Wave 1**: F145-T02, F145-T03  (frontend: SetIconFilter + SortSelect swap; Owned toggle)
- **Wave 2**: F145-T04            (frontend: compact/collapsible rarity+color filters on mobile)

## Global acceptance criteria

- [ ] Set filter uses `SetIconFilter` with Scryfall icons (same as MyCollection)
- [ ] Sort uses `SortSelect` with `CATALOG_SORT_OPTIONS` (name, set, price, rarity, collector number)
- [ ] "Owned" toggle filter shows only cards the user owns when active
- [ ] Rarity + color filter chips remain functional and collapse on mobile
- [ ] All filter state persisted in URL search params (back/forward works)
- [ ] Backend accepts `rarity` and `collector_number` as sort_by values
- [ ] Existing tests pass; new tests cover all new filter interactions
- [ ] Diagrams updated

## Diagrams

- `frontend/docs/diagrams/F145-architecture.mmd`
- `frontend/docs/diagrams/F145-journey.mmd`

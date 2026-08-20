# F11 — Post-F10 Operationalization

**Status:** done

## Summary

Operationalize the production database after F10 shipped: normalize set
codes, run match report, sync collection prices, verify dashboard KPIs.
In parallel, clean up 3 tech debt items identified by the TechLead during
F10 review. All code already exists — this feature is about execution,
verification, and minor refactors.

## Architecture Impact

- `src/collection/converter.py` — **new** shared helper (extracted from 2 modules)
- `src/collectors/match_report.py` — import change only
- `src/collectors/sync_collection.py` — import change + remove dead `BASE_URL`
- `src/database/repository.py` — new method `get_collection_total_value()`
- `src/api/routers/collection.py` — simplified to use Repository method

No schema changes. No new dependencies. No behavioral changes.

## Wave Manifest

- **Wave 0**: F11-T01                         (normalize set codes — prerequisite for all ops)
- **Wave 1**: F11-T02, F11-T03, F11-T04, F11-T05  (match report + all 3 tech debt items in parallel)
- **Wave 2**: F11-T06                         (sync collection — depends on match report review)
- **Wave 3**: F11-T07, F11-T08               (verify dashboard + documentation)

## Global Acceptance Criteria

- [ ] All set codes in `cards` and `source_cards` tables are lowercase
- [ ] Match report generated with coverage stats
- [ ] Collection synced with MYP price data (observations stored)
- [ ] Dashboard shows valid collection KPIs (value, linked count, sets)
- [ ] No duplicated `_row_to_entry` — shared in `src/collection/converter.py`
- [ ] `collection_summary` endpoint uses Repository, no raw SQLAlchemy in router
- [ ] Dead `BASE_URL` removed from `sync_collection.py`
- [ ] All backend tests passing (604+), coverage >= 90%
- [ ] README.md updated with F11 delivery notes

## Diagrams

- `docs/diagrams/F11-architecture.mmd` — data flow: normalize → match → sync → verify
- `docs/diagrams/F11-journey.mmd` — operator journey through the 4-step pipeline

# F11 — Post-F10 Operationalization

## Problem

F10 (Collection-Centric Pivot) shipped code for normalize, match-report,
sync-collection, and DB cleanup, but the production DB has not been
operationalized yet. Additionally, the TechLead identified 3 minor tech
debt items during F10 review.

## Scope

1. **Operational**: run normalize, match-report, sync-collection, verify
   dashboard — all using existing CLI commands.
2. **Tech debt**: 3 small refactors (extract `_row_to_entry`, move raw
   SQLAlchemy to Repository, remove dead `BASE_URL`).
3. **Documentation**: PRD, Mermaid diagrams, README update.

## Constraints

- No new dependencies.
- No schema changes.
- All code changes are refactors — no behavioral changes.
- Operational tasks interact with MYP (rate-limited, ~35-40 min for sync).
- Must back up DB before any destructive operation.

## Acceptance Criteria (summary)

- AC-1: Set codes normalized (all lowercase in cards + source_cards).
- AC-2: Match report generated and reviewed.
- AC-3: Collection synced with MYP price data.
- AC-4: Dashboard shows valid collection KPIs.
- AC-5: `_row_to_entry` extracted to shared module, no duplication.
- AC-6: `collection_summary` uses Repository method, no raw SQLAlchemy in router.
- AC-7: Dead `BASE_URL` removed from sync_collection.py.
- AC-8: All 604+ backend tests passing, coverage >= 90%.

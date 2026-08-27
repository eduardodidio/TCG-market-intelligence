# F75 — Admin Panel Accordion Grouping

**Status:** planned
**Wave structure:** Wave 2 (after F74)
**Dependencies:** F74 (user CRUD must be complete)

## Summary

Reorganize the admin panel from tabs to accordion (sanfona) collapsible sections. Consolidate Liga Status, Schedules, and Scans pages into the admin panel. Remove standalone nav items for admin-only pages.

## Sections (accordion items)

1. **Users** — user list + CRUD + credit adjustments (from F74 + existing)
2. **Dashboard** — KPI cards (existing)
3. **Liga Status** — coverage dashboard (from AdminLigaStatus.tsx)
4. **Schedules** — schedule CRUD (from Schedules.tsx)
5. **Scans** — scan history + trigger (from Scans.tsx)

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| F75-T01 | AccordionSection component + AdminPanel refactor | 2 |
| F75-T02 | Migrate Liga Status, Schedules, Scans into accordion | 2 |
| F75-T03 | Nav cleanup + route consolidation | 2 |
| F75-T04 | Frontend tests | 2 |

## Acceptance Criteria

- Admin panel uses accordion sections instead of tabs
- All 5 sections are collapsible (click header to toggle)
- Only one section open at a time (or multiple — user preference, prefer single)
- Liga Status, Schedules, Scans content embedded inline in accordion
- Old standalone routes (/admin/liga-status, /schedules, /scans) removed from nav
- Non-admin users cannot see admin nav items
- All admin functionality preserved

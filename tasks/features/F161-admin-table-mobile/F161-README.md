# F161 — Admin Table Mobile Overflow

**Status:** planned
**Branch:** homol
**Created:** 2026-09-18
**Source:** `docs/ux-audit-2026-09-18.md`

## Summary

4 admin tables use `overflow-hidden` (clips content) instead of
`overflow-x-auto` (scrollable). Already-correct examples:
AdminPriceRequestsSection, ScheduleTable, ScanHistoryTable.

## Audit Results

**Need fix (4 tables):**
- AdminPanel.tsx (users table, line 535)
- AdminAuditLogSection.tsx (audit log, line 134)
- AdminErrorsSection.tsx (error logs, line 284)
- AdminLigaSection.tsx (missing cards, line 246)

## Tasks

| Task | Title                                    | Files |
|------|------------------------------------------|-------|
| T01  | Wrap admin tables in overflow-x-auto     | AdminPanel.tsx, AdminAuditLogSection.tsx, AdminErrorsSection.tsx, AdminLigaSection.tsx |

## Wave Plan

### Wave 0
- **T01**: Add `<div className="overflow-x-auto">` wrapper around each
  table, matching the pattern in AdminPriceRequestsSection.tsx

**Total: 1 task in 1 wave**

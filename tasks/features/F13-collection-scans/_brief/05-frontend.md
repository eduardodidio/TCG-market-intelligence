# F13 -- Frontend

## New Page: Scans (`/scans`)

### Layout

1. **Header section** -- "Scans" title + "New Scan" button
2. **Scan trigger form** (collapsible, opened by "New Scan"):
   - Scan type dropdown: Collection, By Set, By Format, Custom
   - Conditional filter fields based on type (set code input, format dropdown)
   - Limit input (optional)
   - "Start Scan" button (POST to API)
3. **Scan history table**:
   - Columns: ID, Type, Status (badge), Cards, Processed, Failed, Obs, Started, Duration
   - Status badges: pending (gray), running (blue/pulse), completed (green), failed (red)
   - Clickable rows -> detail view
   - Pagination
4. **Scan detail modal/panel** (on row click):
   - Full metrics
   - Error summary (if any)
   - Filters used

### Components

- `frontend/src/pages/Scans.tsx` -- page component
- `frontend/src/components/ScanForm.tsx` -- trigger form
- `frontend/src/components/ScanHistoryTable.tsx` -- history table
- `frontend/src/hooks/useScans.ts` -- API hooks (list, detail, trigger)

### Navigation

Add "Scans" to the sidebar/nav, between "My Collection" and existing items.

### Patterns to follow

- Use existing `api.ts` fetch wrapper
- Use existing Tailwind utility classes
- Use existing table patterns from MyCollection or Cards pages
- Use existing badge/status patterns from Dashboard

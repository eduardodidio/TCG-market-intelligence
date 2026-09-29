# F184 — Auto-rotating Movers Ticker on Dashboard

**Status:** done

## Goal

Add an auto-rotating ticker bar at the top of the Dashboard that continuously
scrolls through the user's collection movers (gainers and losers) in an infinite
loop, providing at-a-glance market highlights without requiring scroll or
interaction.

## Architecture Impact

- **Frontend only** — no backend or API changes
- `frontend/src/components/` — new `MoversTicker` component
- `frontend/src/pages/Dashboard.tsx` — integrate ticker above KPIs
- `frontend/src/index.css` — reuse existing `animate-ticker` keyframe

## Wave Manifest

- **Wave 0**: F184-T01 (MoversTicker component + CSS)
- **Wave 1**: F184-T02 (Dashboard integration), F184-T03 (diagrams + i18n)

## Acceptance Criteria

1. Dashboard shows a horizontal ticker bar above the KPI cards
2. Ticker scrolls continuously left, showing card name + change % with color
3. Ticker pauses on hover
4. Ticker is hidden when movers data is empty or loading
5. Existing CollectionMovers grid remains below, unchanged
6. Works on mobile (visible, no layout break)
7. Supports dark mode
8. `motion-reduce:` respects prefers-reduced-motion

## Diagrams

- `docs/diagrams/F184-architecture.mmd` — component data-flow
- `docs/diagrams/F184-journey.mmd` — user journey on dashboard

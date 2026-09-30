# F187 -- Unify Dashboard Movers Panels Visual Identity

## Summary

The Dashboard has two movers sections with inconsistent visual identity:
CollectionMovers (card thumbnails, `bg-slate-800` container, price changes with
abs+pct) and TrendingSection in `variant="list"` mode (no thumbnails, `divide-y`
separator style, different hover, different padding). The user wants the "Em
Alta" / "Em Baixa" trending sections to look exactly like CollectionMovers, and
wants the ability to dismiss individual rows from the CollectionMovers panel.

## Scope

Frontend-only. No backend API changes. No new dependencies. No new i18n keys
needed beyond possibly `movers.dismiss` (aria-label for the X button).

## Architecture Decision

- **Do NOT modify TrendingSection** -- it is used elsewhere (Market/Trending
  page) with `variant="cards"` and `variant="list"`. Changing it would risk
  breaking other consumers.
- Instead, create a new **`DashboardTrendingMovers`** component that:
  - Fetches data from the same trending API (`/api/v1/market/trending/{direction}`)
  - Maps `TrendingCardEntry` fields to the `MoverRow` visual contract
  - Renders using the exact same container + row style as `CollectionMovers`
- **Extract `MoverRow`** from `CollectionMovers.tsx` into a standalone export so
  both `CollectionMovers` and `DashboardTrendingMovers` can import it. Add an
  optional `onDismiss` callback prop to `MoverRow` for the dismiss feature.
- The dismiss feature on `CollectionMovers` is session-only (`useState` set of
  dismissed card_ids, reset on page reload).

## Data Shape Mapping

`TrendingCardEntry` -> `MoverRow` props mapping:
| TrendingCardEntry field | MoverRow equivalent      |
|------------------------|--------------------------|
| `card_id`              | `mover.card_id`          |
| `name_en` / `name_pt`  | `mover.card_name` (via `getCardName()`) |
| `set_code`             | `mover.set_code`         |
| `image_url`            | `mover.image_uri`        |
| `change_abs`           | `mover.change_abs`       |
| `change_pct`           | `mover.change_pct`       |

The mapping is straightforward. `DashboardTrendingMovers` will convert the
trending API response into the shape `MoverRow` expects.

## File Ownership

| File | Owner task | Notes |
|------|-----------|-------|
| `CollectionMovers.tsx` | T01 + T02 | T01 extracts MoverRow; T02 adds dismiss. Sequential dependency. |
| `Dashboard.tsx` | T01 | Replaces TrendingSection with DashboardTrendingMovers |
| `DashboardTrendingMovers.tsx` (new) | T01 | New component |
| `Dashboard.test.tsx` | T03 | Test updates for new component mock |
| `DashboardTrendingMovers.test.tsx` (new) | T03 | New test file |
| `CollectionMoversDismiss.test.tsx` (new) | T03 | New test file |
| `en.json` / `pt-BR.json` | T02 | Only adds `movers.dismiss` key |

## Waves

### Wave 0: T01 + T02 (parallel after MoverRow extraction)

T01 and T02 both touch `CollectionMovers.tsx` but in different ways:
- T01 extracts `MoverRow` as a named export (no behavior change)
- T02 adds `onDismiss` prop to `MoverRow` and dismiss state to `CollectionMovers`

**These tasks are NOT parallel** -- T02 depends on T01's `MoverRow` extraction.
T01 must complete first so that T02 can add `onDismiss` to the already-exported
`MoverRow`.

### Wave 0: T01 -- Extract MoverRow + Create DashboardTrendingMovers
### Wave 1: T02 -- Add dismiss to CollectionMovers (depends on T01)
### Wave 1: T03 -- Tests for both T01 and T02 (depends on T01 + T02)

Actually, T03 tests can only be written after T01 and T02 are done (they test
the final behavior). So the Waves are:

- **Wave 0:** T01
- **Wave 1:** T02, T03 (parallel -- T02 touches CollectionMovers, T03 writes
  new test files that do not conflict with T02's source edits)

Wait -- T03 needs to test T02's dismiss behavior, so T03 depends on T02.
Final ordering:

- **Wave 0:** T01
- **Wave 1:** T02 + T03 (T03 depends on both T01 and T02)

Revised: T03 must wait for T02. So:

- **Wave 0:** T01
- **Wave 1:** T02
- **Wave 2:** T03

This is the safest ordering given the file conflicts on `CollectionMovers.tsx`.

## Tasks

| Task | Wave | Type | Depends on | Status |
|------|------|------|-----------|--------|
| T01  | 0    | frontend | -- | planned |
| T02  | 1    | frontend | T01 | planned |
| T03  | 2    | test | T01, T02 | planned |

## Acceptance Criteria

1. "Em Alta" and "Em Baixa" sections on Dashboard use the same container style
   (`bg-slate-800 rounded-lg p-4 border border-slate-600`), card thumbnails
   (h-10 w-7), and price display (abs + pct) as CollectionMovers.
2. Clicking a row in "Em Alta"/"Em Baixa" navigates to `/cards/{card_id}`.
3. Each row in CollectionMovers has an X button that hides it for the session.
4. Dismissed rows do not reappear until page reload.
5. `npm run build` passes with zero errors.
6. All new and modified test files pass.
7. TrendingSection component is unchanged (no regressions on Market/Trending page).

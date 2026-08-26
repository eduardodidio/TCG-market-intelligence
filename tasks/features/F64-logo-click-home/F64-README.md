# F64 — Logo Click Home Navigation

**Status:** shipped
**Created:** 2026-08-26
**Priority:** P2 (UX fix)
**Wave Group:** 0 (independent — parallel with F63, F68, F70)

## Summary

The project logo/title text in the sidebar and mobile header is currently a
plain `<h1>` / `<span>` element. Clicking it should navigate the user back
to the homepage (`/`). This is standard UX — users expect clicking a logo to
go home.

## Acceptance Criteria

1. Clicking the sidebar logo text navigates to `/`
2. Clicking the mobile header logo text navigates to `/`
3. Logo text retains same visual styling (gradient, font size)
4. Cursor changes to pointer on hover
5. No layout shift or visual regression

## Waves

| Wave | Tasks | Description |
|------|-------|-------------|
| 0    | T01   | Wrap logo text in Link component |

## Tasks

- **T01** (Wave 0): Wrap logo text in `<Link to="/">` in Layout.tsx

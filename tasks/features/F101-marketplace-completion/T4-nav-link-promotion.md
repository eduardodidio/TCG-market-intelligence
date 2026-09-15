# T4 — Promote Marketplace Nav Link

**Wave:** 1
**Type:** Frontend
**Depends on:** None
**Estimate:** Small

## User Story

As an authenticated user, I want to see the Marketplace link in the main
navigation (not hidden under "Beta Test") so I can easily access it.

## Current Behavior

In `frontend/src/components/Layout.tsx`, the Marketplace link is in
`BETA_NAV_ITEMS` (line 46):
```tsx
const BETA_NAV_ITEMS: ReadonlyArray<NavItem> = [
  // ...
  { to: "/marketplace", labelKey: "nav.marketplace", requiresAuth: true },
  // ...
];
```

Users must expand the "Beta Test" collapsible section to find it.

## Desired Behavior

Move the Marketplace entry from `BETA_NAV_ITEMS` to `PRIMARY_NAV_ITEMS`.
Place it after "Achievements" and before "Settings":

```tsx
const PRIMARY_NAV_ITEMS: ReadonlyArray<NavItem> = [
  { to: "/", labelKey: "nav.dashboard", requiresAuth: false },
  { to: "/collection", labelKey: "nav.myCollection", requiresAuth: true },
  { to: "/cards", labelKey: "nav.exploreCards", requiresAuth: false },
  { to: "/catalog", labelKey: "nav.catalog", requiresAuth: false },
  { to: "/alerts", labelKey: "nav.alerts", requiresAuth: true },
  { to: "/achievements", labelKey: "nav.achievements", requiresAuth: true },
  { to: "/marketplace", labelKey: "nav.marketplace", requiresAuth: true },  // MOVED
  { to: "/settings", labelKey: "nav.settings", requiresAuth: true },
  { to: "/admin", labelKey: "nav.admin", requiresAuth: true, requiresAdmin: true },
];
```

Remove the duplicate from `BETA_NAV_ITEMS`.

## Dev Notes

### Files to modify:
- `frontend/src/components/Layout.tsx` — move one line between arrays.

### Considerations:
- Verify no other component references `BETA_NAV_ITEMS` length or index for
  the marketplace item.
- The `requiresAuth: true` flag already handles hiding from unauthenticated
  users.

## Testing

### Vitest + React Testing Library:
- `test_marketplace_in_primary_nav` — render Layout with authenticated user,
  verify Marketplace link appears in primary nav section.
- `test_marketplace_not_in_beta_nav` — verify it no longer appears in the
  Beta section.
- `test_marketplace_hidden_when_unauthenticated` — render without auth,
  verify link is not visible.

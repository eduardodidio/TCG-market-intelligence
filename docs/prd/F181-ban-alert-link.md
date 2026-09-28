# F181 -- BanAlertBanner link to banned cards page

## User Story

As a user viewing my collection, when the BanAlertBanner tells me I have
banned or restricted cards, I want to click a link that takes me directly to
the banlist page filtered to my owned cards, so I can see which cards are
affected and in which formats.

## Problem

`BanAlertBanner` displays counts ("3 cards banned, 2 restricted") but provides
no way to navigate to the detailed banlist. The `/banlist?owned=1` page already
exists and supports the `owned=1` query param for filtering to the user's
collection, but there is no link connecting the two.

## Scope

- **Frontend-only** -- no backend changes, no new API endpoints
- **No new components** -- adds a `<Link>` element inside existing `BanAlertBanner`
- **i18n** -- adds `banEngine.viewDetails` key to both locale files

## Acceptance Criteria

1. `BanAlertBanner` renders a clickable link when `bannedCount > 0` or
   `restrictedCount > 0`.
2. The link navigates to `/banlist?owned=1`.
3. The link text uses `t("banEngine.viewDetails")`.
4. i18n keys added: `banEngine.viewDetails` in both `en.json` ("View details")
   and `pt-BR.json` ("Ver detalhes").
5. Existing dismiss button and styling are unchanged.
6. New test asserts the link is rendered with correct `href`.
7. New test asserts the link is NOT rendered when both counts are 0.
8. All existing `BanAlertBanner` tests continue to pass.

## Files Changed

- `frontend/src/components/BanAlertBanner.tsx`
- `frontend/src/i18n/locales/en.json`
- `frontend/src/i18n/locales/pt-BR.json`
- `frontend/tests/components/BanAlertBanner.test.tsx`

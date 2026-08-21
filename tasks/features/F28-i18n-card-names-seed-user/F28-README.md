# F28 — i18n Card Names + Seed User

**Status:** planned
**Created:** 2026-08-21
**Priority:** high

## Summary

Make card names switch between English and Portuguese when user toggles
language. Update seed user data with correct email. Associate existing
collection with the seeded user.

## Problems

1. Card names always show `name_en` regardless of language setting.
   The DB has `name_pt` for many cards but frontend never uses it based
   on language context.
2. Seed user email is `eduardo.didio` but should be
   `eduardorutkoskididio@gmail.com` with password `mudar@123`.
3. MoverEntry API schema only returns `name_en`, not `name_pt` —
   prevents language-based name switching on market movers page.

## Tasks

| Task | Description | Wave |
|------|------------|------|
| T01 | Add `useCardName` hook + update all card name displays | 1 |
| T02 | Add `name_pt` to MoverEntry schema & query | 1 |
| T03 | Update seed-users with correct email + collection association | 1 |

## Waves

- **Wave 1** (parallel): T01, T02, T03 — all independent

## Dependencies

- F22 (authentication) already provides UserRow model
- F24 (i18n) already provides LanguageContext
- Existing collection data in DB to associate with seeded user

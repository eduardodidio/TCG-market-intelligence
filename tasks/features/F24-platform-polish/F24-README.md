# F24 — Platform Polish & Fixes

**Status:** planned
**Depends on:** F23 (all prior features shipped)

## Summary

Batch of bug fixes, UX improvements, and cross-cutting enhancements:
collection card detail fix, missing images/prices in Explore Cards,
dashboard coverage investigation, interactive chart with zoom,
i18n (EN/PT-BR), and full visual redesign aligned with the Lovable
reference app (tcg-market-shine).

## Architecture Impact

- `frontend/src/` — nearly all pages/components touched (style + i18n)
- `frontend/src/components/PriceChart.tsx` — replace with interactive chart (zoom/pan)
- `frontend/src/i18n/` — **new directory**, react-i18next setup + translation files
- `frontend/src/contexts/LanguageContext.tsx` — **new file**, language state
- `frontend/src/pages/CollectionCardDetail.tsx` — fix entry lookup
- `frontend/src/pages/MyCollection.tsx` — fix navigation to card detail
- `frontend/src/pages/Cards.tsx` — fix image resolution + price display
- `frontend/src/components/CardTile.tsx` — image fallback chain fix
- `frontend/src/pages/Dashboard.tsx` — coverage/value investigation + fix
- `src/api/routers/collection.py` — potential backend fix for entry lookup
- `src/database/repository.py` — coverage query improvements

## Wave Manifest

| Wave | Tasks                        | Description                                              |
|------|------------------------------|----------------------------------------------------------|
| 0    | T01, T02                     | i18n infrastructure + Lovable design tokens (parallel)   |
| 1    | T03, T04, T05, T06, T07      | All 5 bug fixes (fully parallel, independent)            |
| 2    | T08, T09                     | i18n string extraction + style overhaul (parallel)       |
| 3    | T10                          | Language selector + integration testing                  |

## Global Acceptance Criteria

- [ ] Collection card click from My Collection opens detail page correctly
- [ ] All Explore Cards show images (Portuguese name fallback to English)
- [ ] Cards without prices show graceful fallback (not blank)
- [ ] Dashboard coverage reflects actual linking state with clear explanation
- [ ] Dashboard collection value accounts for all priced cards
- [ ] Price chart supports zoom in/out, pan, and auto-scales Y-axis
- [ ] UI fully in English by default, with PT-BR language option
- [ ] Language selector on login page and in user settings
- [ ] Visual style matches Lovable reference (colors, typography, spacing, cards)
- [ ] All existing tests pass
- [ ] New tests for changed logic (coverage >= 90%)
- [ ] README.md updated with F24 delivery notes

## Diagrams

- `docs/diagrams/F24-architecture.mmd` — i18n + style system overview
- `docs/diagrams/F24-journey.mmd` — language selection user flow

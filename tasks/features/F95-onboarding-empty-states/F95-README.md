# F95 -- Onboarding & Empty States

## Description

Standardize empty states across all pages with a shared, enhanced EmptyState
component. Add a dismissable welcome banner for first-time users. Replace
all ad-hoc empty state implementations with the shared component, providing
actionable CTAs that guide users toward their next step.

**Status:** planned

## Task List

| Task | Title | Wave | Depends On |
|------|-------|------|------------|
| T01 | Enhance shared EmptyState component | 0 | -- |
| T02 | Welcome banner on first login | 1 | T01 |
| T03 | Dashboard empty states with actionable CTAs | 1 | T01 |
| T04 | Collection page empty state with import CTA | 1 | T01 |
| T05 | Migrate all remaining empty states to shared component | 2 | T01 |
| T06 | i18n keys for all new strings (EN + PT-BR) | 2 | T02, T03, T04 |

## Wave Structure

- **Wave 0 (T01):** Enhance the existing EmptyState component with new props
  (title, description, icon, multiple actions). This is the foundation all
  other tasks consume.
- **Wave 1 (T02, T03, T04):** Three independent page-level tasks that use
  the enhanced component. All parallelizable.
- **Wave 2 (T05, T06):** Migration of remaining pages and i18n consolidation.
  T06 depends on T02-T04 to know the final set of strings.

## Dependencies

- No backend changes required.
- Existing EmptyState component at `frontend/src/components/EmptyState.tsx`.
- Existing i18n setup at `frontend/src/i18n/` with `en.json` and `pt-BR.json`.
- Pages to modify: Dashboard, MyCollection, DeckList, Evaluations, and any
  admin sections with bare empty states.

## Constraints

- Must follow existing Tailwind slate dark theme (slate-900 bg, slate-800
  surface, cyan-400 accent).
- No new dependencies.
- First-login detection via localStorage (set on first successful login).
- All new strings must have both EN and PT-BR translations.

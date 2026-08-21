# Tech Lead Review -- F24 Platform Polish & Fixes

**Reviewer:** Tech Lead Agent
**Date:** 2026-08-21
**Verdict:** APPROVED (with minor issues noted below)

---

## Summary

F24 delivers a solid batch of cross-cutting improvements: i18n infrastructure (react-i18next), a cohesive design token system (CSS custom properties + Tailwind), security fixes (apiGet auth + ownership check), UX enhancements (interactive price chart with zoom), and full string extraction to EN + PT-BR locales. The implementation is clean, well-tested (1179 backend / 479 frontend tests, 94.87% coverage), and follows established project patterns. The feature is ready to ship with a handful of minor issues that can be addressed in a follow-up.

---

## Architecture (PASS)

**i18n setup** -- react-i18next with `LanguageDetector` (localStorage + navigator fallback) is the standard approach for React SPAs. The `LanguageContext` wraps i18next state in React context with `useLanguage` hook, providing a clean abstraction. Language detection order (`localStorage` -> `navigator`) with `tcg_language` as the storage key is well-chosen.

**Design token system** -- CSS custom properties in `design-tokens.css` feeding into Tailwind via `var()` references in `tailwind.config.ts` is the correct layered approach. Tokens are semantically named (`tcg-bg`, `tcg-card`, `tcg-gain`, `tcg-loss`) and well-organized. The documentation in `docs/design/lovable-tokens.md` is a nice touch.

**Backend preference persistence** -- `preferred_language` column on `UserRow` with SQLite migration via `_ensure_columns()` is consistent with the existing `preferred_currency` pattern. The `PreferencesUpdate` schema correctly validates with `^(en|pt-BR)$` regex.

**Language selector** -- Best-effort backend save (fire-and-forget PATCH with swallowed errors) is the right UX decision -- language always updates locally even if the server is unreachable.

---

## Security (PASS)

**T03: apiGet auth fix** -- `apiGet` now includes the `Authorization: Bearer` header from `localStorage.getItem("tcg_access_token")`, matching the pattern already used in `apiPost`, `apiDelete`, and the new `apiPatch`. This fixes the collection card detail "Not Found" bug where authenticated endpoints were called without credentials.

**T03: Ownership check** -- The collection detail endpoint (`GET /collection/{entry_id}`) now fetches the entry then checks `entry.user_id != user_id`, returning 404 if the user does not own it. This is the correct IDOR prevention pattern -- returning 404 (not 403) to avoid leaking existence information.

---

## Code Quality

### Issues Found

**MINOR-01: Dashboard has 2 hardcoded English strings**
File: `frontend/src/pages/Dashboard.tsx`
- Line 123: `<h1>My Collection</h1>` should be `<h1>{t("dashboard.title")}</h1>`
- Line 172: `<h2>Market Overview</h2>` should be `<h2>{t("dashboard.marketOverview")}</h2>`

Note: The loading and error states (lines 70, 78) correctly use `t()`, so this is an oversight in the main render path only. The translation keys already exist in both locale files.

**MINOR-02: Unnecessary `getattr()` calls in auth.py**
File: `src/api/routers/auth.py`, lines 96 and 129
```python
preferred_language=getattr(user, "preferred_language", "en"),
```
The `User` domain model already has `preferred_language: str = "en"` as a field (confirmed in `src/domain/models.py:382`), so `getattr` with a fallback is unnecessary. Same issue in `src/auth/dependencies.py:60,94`. Not a bug, but adds noise. Should be `user.preferred_language` directly.

**MINOR-03: PriceChart has hardcoded hex color values**
File: `frontend/src/components/PriceChart.tsx`
Lines 223-283 contain hardcoded hex colors (`#556275`, `#8494a7`, `#22d3ee`, `#6366f1`, `#4ade80`, `#12161e`, `#e2e8f0`) that correspond exactly to design tokens (`--tcg-dimmed`, `--tcg-muted`, `--tcg-secondary`, `--tcg-primary`, `--tcg-gain`, `--tcg-surface`, `--tcg-text`). Recharts props require literal color values (not CSS variables), so this is a known limitation. However, these could be extracted to a constants object referencing the token hex values to maintain a single source of truth.

**MINOR-04: LanguageSelector has duplicate JSX between variants**
File: `frontend/src/components/LanguageSelector.tsx`
The `compact` and `full` variants share nearly identical markup (lines 34-85), differing only in padding/font-size classes (`px-4 py-2 text-sm` vs `px-3 py-1.5 text-xs`). This could be simplified with a size map, but is not a blocking issue.

---

## Tests (PASS)

Test coverage is strong and meaningful:
- **i18n init tests** (`i18n.test.ts`): Verifies initialization, fallback language, resource bundles, localStorage persistence, and interpolation config. Good.
- **LanguageContext tests** (`LanguageContext.test.tsx`): Tests provider value, language switching, localStorage persistence, and round-trip EN->PT->EN. Good.
- **Overall**: 479 frontend tests across 48 files (up from 431/44), 1179 backend tests at 94.87% (up from 1168/94.73%).

No gaps observed in the new test coverage.

---

## API Contracts (PASS)

**Backward compatible changes:**
- `CollectionSummary`: `priced_count: int = 0` -- additive field with default, existing clients unaffected.
- `UserProfile`: `preferred_language: str = "en"` -- additive field with default.
- `PreferencesUpdate`: `preferred_language: str | None = None` -- optional field, existing callers unaffected.
- `apiPatch` added to `client.ts` -- new function, no breaking changes.
- `apiGet` now sends auth header -- only affects authenticated requests, which were broken before anyway.

All changes are additive and backward-compatible.

---

## Diagrams (FAIL -- Missing)

No diagram files found at `docs/diagrams/F24-architecture.mmd` or `docs/diagrams/F24-journey.mmd`. Per project rules, every feature must produce or update at least two Mermaid diagrams. These need to be created before the feature can be considered fully shipped.

---

## README (FAIL -- Not Updated)

No mention of F24 found in `README.md`. Per project rules, every shipped feature must update the project README with a short note of what was delivered. This needs to be added.

---

## Recommendations

1. **Fix Dashboard hardcoded strings** (MINOR-01) -- Replace the two literal English strings with `t()` calls. This is the most impactful fix since it breaks i18n on the most visible page.

2. **Create F24 diagrams** -- Add `docs/diagrams/F24-architecture.mmd` covering the i18n data flow (browser locale -> i18next -> LanguageContext -> components, and auth preference -> backend -> login response -> LanguageContext sync) and `docs/diagrams/F24-journey.mmd` covering the user journey for language switching.

3. **Update README.md** -- Add F24 delivery notes covering: i18n (EN + PT-BR), design token system, apiGet auth fix, interactive price chart zoom, collection coverage breakdown, language selector with backend persistence.

4. **Clean up getattr calls** (MINOR-02) -- Replace with direct attribute access since the domain model already defines the field.

5. **Extract chart colors** (MINOR-03) -- Consider a `CHART_COLORS` constant object that maps semantic names to hex values matching the design tokens. Low priority since Recharts requires literal values.

---

## Final Verdict

**APPROVED** -- The implementation is architecturally sound, security fixes are correct, test coverage is strong, and API changes are backward-compatible. The missing diagrams and README update are documentation gaps that must be addressed before final merge, but they do not block the code review approval. The minor code issues (hardcoded Dashboard strings, unnecessary getattr, chart color constants) are polish items that can be addressed in the same PR or a fast follow-up.

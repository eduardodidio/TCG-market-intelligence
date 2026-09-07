# F108 - Dark Mode (System-Following + Toggle)

## Summary

Added a theme system with dark/light/system modes. The app was already dark-themed;
this feature adds a light theme option and a system-following toggle that respects
the user's OS preference.

## What Changed

### Wave 0 - Theme Infrastructure (T01)

- **ThemeContext** (`frontend/src/contexts/ThemeContext.tsx`):
  - `Theme` type: `'dark' | 'light' | 'system'`
  - `resolvedTheme`: actual applied theme after resolving system preference
  - Persists to `localStorage` key `tcg_theme`
  - Default: `dark` (preserves existing behavior)
  - System mode: listens to `prefers-color-scheme` media query changes
  - Applies/removes `dark` class on `<html>` element
  - Cross-tab sync via `storage` event

- **useTheme hook** (`frontend/src/hooks/useTheme.ts`)

- **App.tsx**: Wrapped with `ThemeProvider` inside `LanguageProvider`

- **Tailwind config**: `darkMode: 'class'` was already set (no change needed)

### Wave 1 - UI Adjustments (T02 + T03)

**T02: Light theme CSS** - Updated key components with `dark:` prefix variants:
- `Layout.tsx` - sidebar, header, nav items, borders
- `KpiCard.tsx` - card backgrounds, text colors
- `CardTile.tsx` - card backgrounds, text, badges
- `SearchBar.tsx` - input styling
- `Breadcrumb.tsx` - text colors, separators
- `Dashboard.tsx` - headings, market strip, dividers
- `EmptyState.tsx` - icon, title, description, button colors
- `ExchangeRateBanner.tsx` - banner background
- `index.html` - body background and text color

**T03: ThemeToggle component** (`frontend/src/components/ThemeToggle.tsx`):
- Three-button segmented control (sun/moon/monitor icons)
- Integrated in sidebar below language selector
- Follows same visual pattern as CurrencyToggle and LanguageSelector
- `data-testid="theme-toggle"` for test access

### i18n Keys Added

- `theme.selector`, `theme.dark`, `theme.light`, `theme.system`
- Added to both `en.json` and `pt-BR.json`

## Tests

- `ThemeContext.test.tsx` (7 tests): persistence, class application, system preference, cycling
- `ThemeToggle.test.tsx` (5 tests): rendering, button states, theme switching, ARIA
- **Total**: 12 new tests, 0 regressions (1617 total pass)

## Design Decisions

- Dark remains the default to preserve existing user experience
- Light mode targets the ~10 highest-visibility components (not every single one)
- Remaining components inherit reasonable defaults from Tailwind's dark: variants
- matchMedia is guarded against environments where it's unavailable (test/SSR)

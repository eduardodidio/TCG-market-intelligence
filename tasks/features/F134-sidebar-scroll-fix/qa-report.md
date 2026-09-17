# QA Report -- F134

**Verdict:** PASS
**Date:** 2026-09-17

## Test Results

### Layout Tests (F134-specific)
All 24 tests in `frontend/src/components/__tests__/Layout.test.tsx` pass (14 pre-existing collapsible sidebar tests + 10 F134 scroll fix tests).

### Full Frontend Suite
- **204 of 206 test files pass** (2009 of 2010 tests pass)
- **2 pre-existing failures unrelated to F134:**
  1. `TreasureModal.test.tsx` -- expects `glareMaxOpacity` 0.15 but component uses 0.35 (introduced by F130 foil visual enhancement, per git log commit `f545abb`)
  2. `UpdatePrompt.test.tsx` -- imports a component file (`UpdatePrompt.tsx`) that no longer exists (stale test from a prior refactor)

### Build Verification
- `npm run build` completes successfully in 3.60s
- PWA service worker generated (71 precache entries)
- No TypeScript or build errors

## Validation

### Code Review: Layout.tsx Structure
Verified the aside element follows the spec exactly:

1. **aside has `flex flex-col`** -- line 177, added alongside existing transform/transition classes
2. **Header zone wrapped in `flex-shrink-0`** -- line 184, `<div className="flex-shrink-0" data-testid="sidebar-header">` wraps logo, user section, TreasureBalance, AlertBell, CurrencyToggle, LanguageSelector, ThemeToggle (lines 184-271)
3. **Nav zone wrapped in `flex-1 overflow-y-auto`** -- line 272, `<div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-600 dark:scrollbar-thumb-slate-500 scrollbar-track-transparent" data-testid="sidebar-nav-container">` wraps the `<nav>` element (lines 272-350)
4. **InstallPrompt is outside scrollable container** -- line 352-356, direct child of aside with `mt-auto` class, correctly pinned to bottom
5. **Scrollbar plugin installed** -- `tailwind-scrollbar@^3.1.0` in package.json, imported and configured in `tailwind.config.ts` with `nocompatible: true`
6. **No existing functionality broken** -- aside positioning classes (`fixed inset-y-0 left-0`, `md:relative`) unchanged, collapsed/expanded width logic unchanged, mobile overlay logic unchanged

### DOM Structure (verified)
```
<aside class="... flex flex-col" data-testid="sidebar">
  <div class="flex-shrink-0" data-testid="sidebar-header">
    [Logo | User | Controls]
  </div>
  <div class="flex-1 overflow-y-auto scrollbar-..." data-testid="sidebar-nav-container">
    <nav data-testid="sidebar-nav">
      [Primary items + Beta Test]
    </nav>
  </div>
  <div class="mt-auto">
    <InstallPrompt />
  </div>
</aside>
```

## Issues Found

None related to F134. The 2 pre-existing test failures should be tracked separately:
- `TreasureModal.test.tsx` needs `glareMaxOpacity` expectation updated from 0.15 to 0.35
- `UpdatePrompt.test.tsx` references a deleted component file and should be removed or updated

## Test Gaps Filled

Added 2 tests to `frontend/src/components/__tests__/Layout.test.tsx`:

1. **"dark mode scrollbar class is present on nav container"** -- verifies `dark:scrollbar-thumb-slate-500` class exists on the scrollable container, ensuring dark mode gets a visible scrollbar thumb
2. **"flex layout persists when sidebar is collapsed"** -- sets `sidebar-collapsed=true` in localStorage, then verifies `flex`/`flex-col` on aside, `flex-shrink-0` on header, and `flex-1`/`overflow-y-auto` on nav container all remain present in collapsed state

Total F134 test count: 10 (8 original + 2 added by QA)

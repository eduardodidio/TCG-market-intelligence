# F25 — Revert Lovable Styling

**Status:** planned
**Depends on:** F24 (all prior features shipped)

## Summary

Revert the Lovable/tcg-* design system introduced in F24-T09 and restore the
original Tailwind slate-based dark theme. Remove all Lovable-related
documentation and CSS custom properties. All F24 functionality (i18n, bug
fixes, interactive chart, auth fixes) is preserved — only the visual layer
changes back.

## Architecture Impact

- `frontend/tailwind.config.ts` — revert to minimal config (only `colors.surface`)
- `frontend/src/index.css` — remove design-tokens import, restore `bg-slate-900 text-slate-100`
- `frontend/src/styles/design-tokens.css` — **delete**
- `docs/lovable/LOVABLE_PROMPT.md` — **delete**
- `docs/design/lovable-tokens.md` — **delete**
- 35 component/page files — replace ~317 `tcg-*` class occurrences with slate equivalents
- Test files — update class assertions referencing `tcg-*`

## Color Mapping Reference

| Lovable token (tcg-*)        | Slate equivalent            |
|------------------------------|-----------------------------|
| `bg-tcg-bg`                  | `bg-slate-900`              |
| `bg-tcg-surface`             | `bg-slate-800`              |
| `bg-tcg-card`                | `bg-slate-800`              |
| `bg-tcg-card-alt`            | `bg-slate-700`              |
| `border-tcg-border`          | `border-slate-600`          |
| `border-tcg-ring`            | `border-slate-500`          |
| `text-tcg-text`              | `text-slate-100`            |
| `text-tcg-muted`             | `text-slate-400`            |
| `text-tcg-dimmed`            | `text-slate-500`            |
| `text-tcg-primary`           | `text-indigo-400`           |
| `bg-tcg-primary`             | `bg-indigo-500`             |
| `hover:bg-tcg-primary-hover` | `hover:bg-indigo-400`       |
| `text-tcg-secondary`         | `text-cyan-400`             |
| `text-tcg-accent`            | `text-purple-400`           |
| `text-tcg-gain`              | `text-green-400`            |
| `text-tcg-loss`              | `text-red-400`              |
| `text-tcg-warning`           | `text-amber-400`            |
| `text-tcg-info`              | `text-sky-400`              |
| `shadow-tcg-*`               | `shadow-md` / `shadow-lg`   |
| `rounded-tcg-*`              | `rounded-md` / `rounded-lg` |
| `font-tcg-sans`              | (default sans-serif)        |
| `font-tcg-mono`              | `font-mono`                 |
| `bg-tcg-gradient-*`          | (remove or replace inline)  |

## Wave Manifest

| Wave | Tasks           | Description                                              |
|------|-----------------|----------------------------------------------------------|
| 0    | T01             | Revert config files + delete Lovable docs/tokens         |
| 1    | T02, T03, T04   | Revert components (layout+nav, cards+data, pages)        |
| 2    | T05             | Fix tests + full regression                              |

## Global Acceptance Criteria

- [ ] No `tcg-` CSS custom properties or Tailwind classes remain in codebase
- [ ] `design-tokens.css` deleted
- [ ] `docs/lovable/` and `docs/design/lovable-tokens.md` deleted
- [ ] `tailwind.config.ts` matches pre-F24 state (only `colors.surface`)
- [ ] `index.css` uses `bg-slate-900 text-slate-100 antialiased`
- [ ] All pages render correctly with slate dark theme
- [ ] All F24 features work (i18n, chart zoom, auth, bug fixes)
- [ ] All existing tests pass
- [ ] README.md updated

## Diagrams

- No new diagrams needed (this is a revert, not new architecture)
- Remove F24 diagram references to Lovable if present

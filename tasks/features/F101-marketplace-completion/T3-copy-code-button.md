# T3 — Copy Code Button

**Wave:** 1
**Type:** Frontend
**Depends on:** None
**Estimate:** Small

## User Story

As a user browsing the marketplace, I want to copy a seller's share code with
one click so I can send it to a friend or save it for later.

## Current Behavior

Share codes appear truncated at the bottom of each `MarketplaceCardTile`:
```tsx
<div className="text-[10px] text-slate-500 text-center mt-1">
  {listing.share_code.slice(0, 8)}...
</div>
```

There is no way to copy the full code.

## Desired Behavior

Replace the truncated text with a clickable `CopyCodeButton` component:
- Shows the truncated code (e.g., `abc12345...`).
- On click, copies the full share code to clipboard via `navigator.clipboard.writeText()`.
- Visual feedback: briefly changes text/icon to a checkmark or "Copied!" for
  1.5 seconds, then reverts.
- Tooltip or title attribute showing the full code on hover.
- Also show the copy button on the Settings page sharing section (where the
  user sees their own share code after enabling sharing).

## Dev Notes

### New files:
- `frontend/src/components/CopyCodeButton.tsx` — reusable component.

### Files to modify:
- `frontend/src/pages/Marketplace.tsx` — replace the truncated share_code div
  in `MarketplaceCardTile` with `<CopyCodeButton code={listing.share_code} />`.
- `frontend/src/i18n/locales/en.json` — add `marketplace.codeCopied` key.
- `frontend/src/i18n/locales/pt-BR.json` — add corresponding key.

### Component API:
```tsx
interface CopyCodeButtonProps {
  code: string;
  truncateAt?: number;  // default 8
  className?: string;
}
```

### Implementation:
- Use `useState` for the "copied" feedback state.
- `navigator.clipboard.writeText(code)` is async — handle the promise.
- Fallback for older browsers: use a hidden textarea + `document.execCommand('copy')`.
- Apply `dark:` variants for dark mode compatibility.
- Stop event propagation so clicking the copy button does not trigger the
  parent card's click handler (if any).

## Testing

### Vitest + React Testing Library:
- `test_renders_truncated_code` — verify displayed text is truncated.
- `test_copies_to_clipboard_on_click` — mock `navigator.clipboard.writeText`,
  verify it is called with the full code.
- `test_shows_copied_feedback` — click, verify "Copied" text appears.
- `test_reverts_after_timeout` — after 1.5s, verify original text returns.
- `test_full_code_in_title_attribute` — verify title/tooltip shows full code.

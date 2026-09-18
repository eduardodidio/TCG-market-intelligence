# T1 — Sidebar Thumbnail Pulsing Golden Glow

**Wave:** 1
**Depends on:** none

## User Story

As a user, I want the treasure token thumbnail in the sidebar to have a subtle
pulsing golden glow so it feels alive and precious, matching the treasure theme.

## Dev Notes

### Current State

`TreasureBalance.tsx` line 47 — the `<img>` has:
```
className="w-12 h-16 rounded object-cover border border-amber-500/50 shadow-lg ..."
```
This is a static shadow with no animation. The user reports "o tesouro perdeu o
seu brilhozinho" — the golden shine is missing.

### Implementation

1. **Create CSS keyframe** `treasure-pulse-glow` in a new file
   `frontend/src/styles/treasure-glow.css` (or append to `foil-shimmer.css`):

   ```css
   @keyframes treasure-pulse-glow {
     0%, 100% {
       box-shadow:
         0 0 8px 2px rgba(245, 158, 11, 0.3),
         0 0 20px 4px rgba(245, 158, 11, 0.15);
     }
     50% {
       box-shadow:
         0 0 14px 4px rgba(245, 158, 11, 0.5),
         0 0 30px 8px rgba(245, 158, 11, 0.25);
     }
   }

   .treasure-glow {
     animation: treasure-pulse-glow 3s ease-in-out infinite;
   }
   ```

   Respect `prefers-reduced-motion: reduce` — disable animation.

2. **Apply class** to the `<img>` in `TreasureBalance.tsx`:
   - Import the CSS file
   - Add `treasure-glow` class to the `<img>` className
   - Keep existing `border-amber-500/50` and `shadow-lg` (the animation
     overrides box-shadow, but the border stays)

3. **Hover enhancement** (optional): on hover, intensify the glow slightly
   via `.treasure-glow:hover` with a brighter box-shadow.

### Key Constraints

- The glow must be subtle — not distracting in the sidebar
- Must not cause layout shifts (box-shadow does not affect layout)
- Duration 2.5-3.5s feels organic; avoid fast pulsing
- Keep the `cursor-pointer` and `hover:border-amber-400` transition

## Testing

- Unit test: verify the `<img>` element has `treasure-glow` class
- Visual: confirm golden pulse is visible in dark and light themes
- Reduced motion: confirm animation is disabled with `prefers-reduced-motion`

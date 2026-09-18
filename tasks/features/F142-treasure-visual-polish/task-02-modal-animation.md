# T2 — Modal Animation Refinement + Golden Shimmer

**Wave:** 1
**Depends on:** none

## User Story

As a user, I want the treasure modal to open and close with a smooth, elegant
motion (no bounce overshoot) and display a warm golden shimmer on the card
while open, making the treasure feel luxurious.

## Dev Notes

### Current State

`TreasureModal.tsx`:
- **Easing:** `cubic-bezier(0.34, 1.56, 0.64, 1)` — this overshoots (bouncy
  spring). The `1.56` control point causes the element to fly past its target
  and bounce back. User wants "deslocamento mais elegante."
- **Open state:** static `transform: scale(1) translate(0, 0)` — no float.
- **Box-shadow:** large golden glow when open (line 177-179), static.
- **Foil shimmer:** rainbow from `foil-shimmer.css` via Card3DTilt `foil={true}`.

### Implementation

#### A. Smoother Easing Curve

Replace the bouncy cubic-bezier with an elegant ease-out curve on line 118:

```
Current:  cubic-bezier(0.34, 1.56, 0.64, 1)
Proposed: cubic-bezier(0.16, 1, 0.3, 1)
```

This is a smooth deceleration curve — fast start, graceful settle, no overshoot.
Apply to both transform and opacity transitions.

Consider slightly increasing `ANIM_DURATION` from 500ms to 600ms for a more
deliberate, elegant feel.

#### B. Gentle Float While Open

Add a subtle continuous floating animation to the content wrapper when
`phase === "open"`:

```css
@keyframes treasure-float {
  0%, 100% { transform: translateY(0px); }
  50%      { transform: translateY(-6px); }
}
```

Apply via inline style or CSS class when `isOpen`:
- `animation: treasure-float 4s ease-in-out infinite`
- This gives the card a gentle hovering effect while the modal is open
- The float animation should NOT conflict with the enter/leave transform
  transition — apply it only after the enter transition completes (use a
  short delay or switch to the float class after ANIM_DURATION)

#### C. Golden Shimmer Overlay

Add a warm golden shimmer overlay on top of (or alongside) the existing
rainbow foil. Two approaches:

**Option 1 (preferred):** Add CSS class `treasure-golden-shimmer` as a
sibling `::before` pseudo-element on the modal image wrapper:

```css
@keyframes golden-shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.treasure-golden-shimmer::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    105deg,
    transparent 30%,
    rgba(255, 215, 0, 0.15) 45%,
    rgba(245, 158, 11, 0.25) 50%,
    rgba(255, 215, 0, 0.15) 55%,
    transparent 70%
  );
  background-size: 200% 100%;
  animation: golden-shimmer 3s ease-in-out infinite;
  pointer-events: none;
  border-radius: inherit;
  z-index: 1;
  mix-blend-mode: screen;
}
```

**Option 2:** Wrap the `<img>` inside the Card3DTilt in an extra `<div>`
with the shimmer class. This keeps the rainbow foil from Card3DTilt and
adds a warm golden sweep on top.

Place these keyframes in `treasure-glow.css` (same file as T1).

#### D. Pulsing Box-Shadow on Modal Image

Make the existing static golden box-shadow (line 177) pulse gently while
open, reusing the `treasure-pulse-glow` keyframe from T1 but with larger
values appropriate for the full-size modal image:

```css
.treasure-modal-glow {
  animation: treasure-modal-pulse 3s ease-in-out infinite;
}

@keyframes treasure-modal-pulse {
  0%, 100% {
    box-shadow:
      0 0 80px 20px rgba(245, 158, 11, 0.35),
      0 0 120px 40px rgba(245, 158, 11, 0.12),
      0 25px 50px -12px rgba(0, 0, 0, 0.6);
  }
  50% {
    box-shadow:
      0 0 100px 30px rgba(245, 158, 11, 0.5),
      0 0 150px 50px rgba(245, 158, 11, 0.2),
      0 25px 50px -12px rgba(0, 0, 0, 0.6);
  }
}
```

### Key Constraints

- Keep ALL existing mechanics: sparkle particles, origin-rect fly-back,
  click-to-open, escape-to-close, Card3DTilt with foil
- The float animation must not run during enter/leave — only while `open`
- Respect `prefers-reduced-motion: reduce` for all new animations
- The golden shimmer should complement (not replace) the rainbow foil
- Do not change `SPARKLE_COUNT`, sparkle generation, or portal behavior

## Testing

- Unit test: verify easing curve in `contentStyle.transition` matches the
  new cubic-bezier value
- Unit test: verify float animation class/style is applied when phase is `open`
- Unit test: verify golden shimmer element or class is present on the modal image
- Visual: confirm smooth open/close with no bounce overshoot
- Visual: confirm gentle float is visible while modal stays open
- Visual: confirm warm golden sweep over the card image
- Reduced motion: confirm all new animations are disabled

# 0008 — Dragon Mascot & Premium Branding

**Date:** 2026-08-26
**Status:** CONCEPT
**Deciders:** Eduardo Didio

## Context

The platform lacks a distinctive visual identity beyond the standard dark-theme
UI. An Elder Dragon character — a nod to Magic: The Gathering's iconic creature
type — would serve as the platform mascot, adding personality and reinforcing
the TCG theme. The dragon sits atop a pile of treasure tokens, tying into the
credit/token economy (F65) and subscription plans (ADR-0007).

Key motivations:

- **Brand identity**: A memorable mascot differentiates the platform from
  generic price trackers.
- **Monetization UX**: The dragon can "negotiate" with users during credit
  purchase and subscription flows, making transactional UI more engaging.
- **Cultural fit**: Elder Dragons are deeply embedded in MTG lore; the treasure
  token pile connects game mechanics to the platform's credit system.

## Decision

Document the creative direction for a future design phase. No design assets or
implementation in this ADR.

### Visual Concept

- **Character**: Elder Dragon (stylized, friendly but imposing) perched on a
  pile of treasure tokens.
- **Style**: Semi-flat illustration with subtle gradients, compatible with the
  dark slate theme. Designed at multiple sizes (icon, card, full illustration).
- **Personality**: Wise, slightly mischievous hoarder. Protective of its
  treasure but willing to negotiate.

### Planned Usage

| Location                | Dragon State            | Purpose                          |
|-------------------------|-------------------------|----------------------------------|
| Subscription page       | Seated on treasure pile | Plan selection / upgrade prompt  |
| Credit purchase flow    | Offering tokens         | Transaction confirmation         |
| Loading screens         | Sleeping on hoard       | Loading indicator                |
| Empty states            | Searching / confused    | No-data placeholder              |
| Achievement unlocks     | Celebrating             | Gamification feedback            |

### Implementation Path

1. **Phase 1**: Static SVG illustrations (3-4 poses) for key UI locations.
2. **Phase 2**: Lottie animations for loading screens and transitions.
3. **Phase 3**: Interactive dragon on subscription page (reacts to plan
   selection, "negotiates" pricing).

### Design Constraints

- Must work at 24x24px (nav icon) through 400x400px (hero illustration).
- Color palette must complement the existing slate/cyan dark theme.
- Animations must not exceed 100KB per Lottie file for performance.
- Accessible: animations respect `prefers-reduced-motion`.

## Consequences

- **Easier**: Brand recognition, more engaging monetization flows, emotional
  connection with users.
- **Harder**: Requires design investment (illustration + animation), asset
  management, consistent character across all contexts.
- **Trade-offs**: Custom illustration costs time/money vs. generic UI. Risk of
  the mascot feeling gimmicky if not executed well.

## Alternatives Considered

- **Abstract logo only** — rejected because it lacks personality and does not
  leverage the TCG theme.
- **Multiple mascots per TCG** — rejected for now; a single dragon keeps
  branding simple. Can expand later if the platform supports multiple TCGs.
- **User-selected avatars** — complementary feature, not a replacement for a
  platform mascot.

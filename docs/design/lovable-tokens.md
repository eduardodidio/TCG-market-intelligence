# Lovable Design Tokens -- TCG Market Intelligence

Extracted from the [Lovable reference app](https://tcg-market-shine.lovable.app)
and supplemented with modern TCG/trading platform conventions.

## Theme

Dark-themed. Deep navy/charcoal backgrounds, light text, vibrant accents.

## Color Palette

### Backgrounds
| Token           | Hex       | Usage                                    |
|-----------------|-----------|------------------------------------------|
| `tcg-bg`        | `#0b0e14` | Root page background (deepest layer)     |
| `tcg-surface`   | `#12161e` | Sidebar, panels, raised containers       |
| `tcg-card`      | `#1a1f2e` | Card/tile backgrounds                    |
| `tcg-card-alt`  | `#212737` | Hover/alternate card bg, inputs          |

### Borders & Dividers
| Token           | Hex       | Usage                                    |
|-----------------|-----------|------------------------------------------|
| `tcg-border`    | `#2a3040` | Default border color                     |
| `tcg-ring`      | `#3b4560` | Focus ring, highlighted borders          |

### Text
| Token           | Hex       | Usage                                    |
|-----------------|-----------|------------------------------------------|
| `tcg-text`      | `#e2e8f0` | Primary text (slate-200 equiv)           |
| `tcg-muted`     | `#8494a7` | Secondary/muted text                     |
| `tcg-dimmed`    | `#556275` | Tertiary/placeholder text                |

### Accent Colors
| Token           | Hex       | Usage                                    |
|-----------------|-----------|------------------------------------------|
| `tcg-primary`   | `#6366f1` | Primary action buttons (indigo-500)      |
| `tcg-primary-hover` | `#818cf8` | Hovered primary (indigo-400)        |
| `tcg-secondary` | `#22d3ee` | Data highlights, links (cyan-400)        |
| `tcg-accent`    | `#a78bfa` | Special accents (violet-400)             |

### Semantic Colors
| Token           | Hex       | Usage                                    |
|-----------------|-----------|------------------------------------------|
| `tcg-gain`      | `#4ade80` | Positive price movement (green-400)      |
| `tcg-loss`      | `#f87171` | Negative price movement (red-400)        |
| `tcg-warning`   | `#fbbf24` | Warnings, stale indicators (amber-400)   |
| `tcg-info`      | `#38bdf8` | Info states (sky-400)                    |

### Gradients
| Token               | Value                                      | Usage                    |
|----------------------|--------------------------------------------|--------------------------|
| `tcg-gradient-hero`  | `linear(135deg, #6366f1, #a78bfa, #22d3ee)` | Hero banners, CTAs      |
| `tcg-gradient-card`  | `linear(180deg, #1a1f2e, #12161e)`          | Subtle card depth       |
| `tcg-gradient-glow`  | `radial(circle, #6366f140 0%, transparent 70%)` | Background glow    |

## Typography

| Token         | Value                                         |
|---------------|-----------------------------------------------|
| Font family   | `Inter, system-ui, -apple-system, sans-serif` |
| Font mono     | `JetBrains Mono, Fira Code, monospace`        |
| Size xs       | `0.75rem` (12px)                              |
| Size sm       | `0.875rem` (14px)                             |
| Size base     | `1rem` (16px)                                 |
| Size lg       | `1.125rem` (18px)                             |
| Size xl       | `1.25rem` (20px)                              |
| Size 2xl      | `1.5rem` (24px)                               |
| Size 3xl      | `1.875rem` (30px)                             |
| Weight normal | `400`                                         |
| Weight medium | `500`                                         |
| Weight semibold | `600`                                       |
| Weight bold   | `700`                                         |

## Border Radius

| Token      | Value    | Usage                     |
|------------|----------|---------------------------|
| `tcg-sm`   | `0.375rem` | Small chips, badges     |
| `tcg-md`   | `0.5rem`   | Buttons, inputs         |
| `tcg-lg`   | `0.75rem`  | Cards, panels           |
| `tcg-xl`   | `1rem`     | Modals, large cards     |
| `tcg-2xl`  | `1.5rem`   | Hero sections           |
| `tcg-full` | `9999px`   | Pills, avatars          |

## Shadows

| Token            | Value                                                  | Usage              |
|------------------|--------------------------------------------------------|--------------------|
| `tcg-sm`         | `0 1px 2px rgba(0,0,0,0.3)`                           | Subtle depth       |
| `tcg-md`         | `0 4px 6px -1px rgba(0,0,0,0.4)`                     | Cards              |
| `tcg-lg`         | `0 10px 15px -3px rgba(0,0,0,0.5)`                   | Dropdowns, modals  |
| `tcg-glow`       | `0 0 20px rgba(99,102,241,0.15)`                      | Primary glow       |
| `tcg-glow-cyan`  | `0 0 20px rgba(34,211,238,0.15)`                      | Cyan accent glow   |

## Design Patterns Observed

1. **Glass-morphism on panels**: `backdrop-blur-sm` with semi-transparent backgrounds
   (`bg-[color]/80` patterns) for overlaid panels.
2. **Subtle gradients**: Cards use slight vertical gradients for depth rather than flat
   single-color backgrounds.
3. **Glow accents**: Primary actions emit soft colored shadows (glow effect).
4. **Consistent border treatment**: All containers have 1px borders in `tcg-border` color.
5. **Hover transitions**: Border color shifts to accent on hover with `transition-colors`.
6. **Dark-on-dark layering**: Three depth levels (bg < surface < card) create visual
   hierarchy without relying on shadows alone.

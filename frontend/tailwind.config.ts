import type { Config } from 'tailwindcss';

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      /* ── Existing tokens (preserved) ─────────────────────── */
      colors: {
        surface: {
          DEFAULT: '#1e293b', // slate-800 (original)
        },

        /* ── TCG Design System (Lovable-inspired) ──────────── */
        'tcg-bg': 'var(--tcg-bg)',
        'tcg-surface': 'var(--tcg-surface)',
        'tcg-card': 'var(--tcg-card)',
        'tcg-card-alt': 'var(--tcg-card-alt)',
        'tcg-border': 'var(--tcg-border)',
        'tcg-ring': 'var(--tcg-ring)',
        'tcg-text': 'var(--tcg-text)',
        'tcg-muted': 'var(--tcg-muted)',
        'tcg-dimmed': 'var(--tcg-dimmed)',
        'tcg-primary': {
          DEFAULT: 'var(--tcg-primary)',
          hover: 'var(--tcg-primary-hover)',
          foreground: 'var(--tcg-primary-foreground)',
        },
        'tcg-secondary': {
          DEFAULT: 'var(--tcg-secondary)',
          hover: 'var(--tcg-secondary-hover)',
        },
        'tcg-accent': {
          DEFAULT: 'var(--tcg-accent)',
          hover: 'var(--tcg-accent-hover)',
        },
        'tcg-gain': 'var(--tcg-gain)',
        'tcg-loss': 'var(--tcg-loss)',
        'tcg-warning': 'var(--tcg-warning)',
        'tcg-info': 'var(--tcg-info)',
      },

      /* ── Shadows ─────────────────────────────────────────── */
      boxShadow: {
        'tcg-sm': 'var(--tcg-shadow-sm)',
        'tcg-md': 'var(--tcg-shadow-md)',
        'tcg-lg': 'var(--tcg-shadow-lg)',
        'tcg-glow': 'var(--tcg-shadow-glow)',
        'tcg-glow-cyan': 'var(--tcg-shadow-glow-cyan)',
      },

      /* ── Border Radius ───────────────────────────────────── */
      borderRadius: {
        'tcg-sm': 'var(--tcg-radius-sm)',
        'tcg-md': 'var(--tcg-radius-md)',
        'tcg-lg': 'var(--tcg-radius-lg)',
        'tcg-xl': 'var(--tcg-radius-xl)',
        'tcg-2xl': 'var(--tcg-radius-2xl)',
      },

      /* ── Typography ──────────────────────────────────────── */
      fontFamily: {
        'tcg-sans': ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        'tcg-mono': [
          'JetBrains Mono',
          'Fira Code',
          'ui-monospace',
          'monospace',
        ],
      },

      /* ── Gradients (via backgroundImage) ─────────────────── */
      backgroundImage: {
        'tcg-gradient-hero':
          'linear-gradient(135deg, #6366f1, #a78bfa, #22d3ee)',
        'tcg-gradient-card':
          'linear-gradient(180deg, #1a1f2e, #12161e)',
        'tcg-gradient-glow':
          'radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)',
      },
    },
  },
  plugins: [],
} satisfies Config;

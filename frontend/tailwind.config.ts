import type { Config } from 'tailwindcss';

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        figtree: ['Figtree', 'system-ui', 'sans-serif'],
      },
      colors: {
        surface: {
          DEFAULT: '#1e293b', // slate-800
        },
        v2: {
          bg: '#0a0e1a',
          surface: '#111827',
          'surface-hover': '#1a2332',
          border: 'rgba(255,255,255,0.06)',
          accent: '#06b6d4',
          'accent-soft': 'rgba(6,182,212,0.15)',
          muted: '#94a3b8',
        },
      },
      spacing: {
        'fluid-sm': 'clamp(0.5rem, 1.5vw, 1rem)',
        'fluid-md': 'clamp(1rem, 3vw, 2rem)',
        'fluid-lg': 'clamp(2rem, 5vw, 4rem)',
      },
      borderRadius: {
        v2: '0.75rem',
      },
      boxShadow: {
        'v2-card': '0 4px 24px rgba(0,0,0,0.3)',
        'v2-glow': '0 0 20px rgba(6,182,212,0.15)',
      },
      keyframes: {
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in-out': {
          '0%': { opacity: '0' },
          '10%': { opacity: '1' },
          '80%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
      },
      animation: {
        'fade-in-up': 'fade-in-up 0.3s ease-out',
        'fade-in-out': 'fade-in-out 1.5s ease-in-out forwards',
      },
    },
  },
  plugins: [],
} satisfies Config;

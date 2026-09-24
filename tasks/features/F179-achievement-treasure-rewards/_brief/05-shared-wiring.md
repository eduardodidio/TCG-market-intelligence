# 05 — Shared-file wiring (last Wave, T09 only)

Minimal edits to high-conflict files, nothing else:

1. `src/cli/main.py` — 2 lines before `if __name__ == "__main__":`
   (see `03-backfill.md`).
2. `frontend/src/components/Layout.tsx` — import
   `AchievementNotifierHost` and render `<AchievementNotifierHost />` once, just
   before/after `<main ... data-testid="main-content">` (inside the component's
   root so it has router context). No other changes.
3. `README.md` — add a short "F179 — Achievement Treasure rewards" note in the
   features/changelog area following the existing style: tiers table (one line
   each), new/changed endpoints (`GET /api/v1/achievements` reward fields,
   `POST /api/v1/achievements/check` rewards + balance), new CLI
   `python -m src.cli.main backfill-achievement-rewards [--dry-run] [--user-id N]`,
   toast now shown app-wide.
4. `frontend/src/components/__tests__/Layout.test.tsx` — if Layout tests break
   because the host calls the API on mount, mock `../AchievementNotifierHost`
   (`vi.mock`) to render null.

No `bats/` file is needed: the lazy backfill covers users as they log in, and
the one-off CLI can be run manually against Neon.

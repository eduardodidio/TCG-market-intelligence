# 04 — Routing, menu, routine (.bat), docs

## F177-T09 (Wave 3, hotspot: App.tsx + Layout.tsx)
- `frontend/src/components/Layout.tsx:77`: delete the nav item
  `{ to: "/banlist/history", labelKey: "nav.banHistory", ... }`. Keep the `/banlist` item.
- `frontend/src/App.tsx`: remove the `BanHistory` lazy import (lines ~54-56). Replace the
  `/banlist/history` route element with `<Navigate to="/banlist" replace />` (import `Navigate`
  from react-router-dom if not already imported). Keep the path declared so old bookmarks work.
- Delete `frontend/src/pages/BanHistory.tsx` and `frontend/tests/pages/BanHistory.test.tsx`
  (the page is gone; history now lives in BanCardDetailModal). Use `git rm` on these two files only.
  Before deleting, grep for other importers of `pages/BanHistory`. There must be none besides App.tsx.
- `frontend/tests/components/Layout.test.tsx:368-370`: update the test. It must assert that
  there is NO "Ban History" link in the nav and that the "Ban List" link still exists.
- Add a test (in `frontend/tests/App*.test.tsx` if one exists, else `frontend/tests/routes/banlistRedirect.test.tsx`)
  checking that `/banlist/history` renders the BanList page (`page-banlist`).
- The minimal diff on hotspot files is intentional (the batch runs in parallel).

## F177-T10 (Wave 3, hotspot: bats/ + README.md)
- NEW `bats/banlist-sync.bat`, following `bats/process-queue.bat` exactly:
  ```bat
  @echo off
  REM ============================================================
  REM  banlist-sync.bat — Sincroniza legalidades/banlist do Scryfall
  REM  Sugestao: Windows Task Scheduler diario (ex.: 06:00) ou semanal
  REM ============================================================
  cd /d "%~dp0\.."
  echo ============================================================
  echo  TEDHC Banlist Sync - %date% %time%
  echo ============================================================
  python -m src.cli.main banlist-sync
  if errorlevel 1 (
    echo  [ERRO] banlist-sync falhou - veja o log acima
    exit /b 1
  )
  echo.
  echo  [DONE] %date% %time%
  echo ============================================================
  ```
  CRLF line endings are not required (the existing bat is LF). Match whatever `process-queue.bat` uses.
- `README.md`: add an "F177 — Ban list" note covering the sync fix (JSONL/gzip/redirect/set-code
  mapping, compact storage, batched writes, fails loudly), `bats/banlist-sync.bat` + the
  suggested Task Scheduler cadence, `GET /api/v1/banlist?owned_only=true`,
  `GET /api/v1/banlist/status`, the grouped ban list, the card detail modal with history,
  and the `/banlist/history` → `/banlist` redirect (menu item removed).
- Re-check `docs/diagrams/F177-architecture.mmd` / `F177-journey.mmd` against the final code
  and adjust them if the implementation diverged.
- Do NOT touch `render.yaml` (CI/CD requires explicit user confirmation). The README can mention that
  production is refreshed by running the bat locally (it writes to Neon via `.env`) or via
  `POST /api/v1/banlist/sync` (auth).

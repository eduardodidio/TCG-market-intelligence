# F178 — Component: CLI module + Windows routine

## `src/cli/news_cmd.py` (NEW — owner F178-T04)
```python
import click

def _resolve_db(ctx, param, value):
    """Same contract as src/cli/main.py:_resolve_db (lines 20-26)."""
    if value is None:
        from src.config import get_db_url
        return get_db_url()
    return value
```
**Circular-import gotcha:** `main.py` will import `news_cmd`, so `news_cmd`
must NOT import `src.cli.main`. Duplicate the 5-line `_resolve_db` callback
locally (it only delegates to `src.config.get_db_url`) — `.env` → Neon
`DATABASE_URL` is picked up automatically, SQLite fallback otherwise.

Command:
```
fetch-news [--db URL] [--max-per-source N=20] [--check-sources] [--source NAME ...]
```
- `--check-sources`: dry run (`fetch_news(None, dry_run=True, ...)`), prints table
  `name | ok | http | entries | error`, never writes.
- `--source NAME` (multiple): restrict to named sources (case-insensitive); unknown name → `click.UsageError`.
- Prints the same summary block as the old command (Fetched/New/Skipped/Errors) plus per-source lines.
- Exit code: `0` if at least one source ok; `1` if all sources failed (so the `.bat` can show FAIL).
- Declare `news_cmd = click.command("fetch-news")(...)` as a standalone
  `click.Command` object named `fetch_news_command` for `cli.add_command(...)`.

## `src/cli/main.py` (shared — owner F178-T07, last wave)
- Delete the inline `@cli.command("fetch-news")` block (`fetch_news_cmd`, ~lines 2792-2818).
- Add the registration right before `if __name__ == "__main__":` (currently ~line 3168):
  ```python
  from src.cli.news_cmd import fetch_news_command  # noqa: E402  (F178)
  cli.add_command(fetch_news_command)
  ```
  Other batch features may add similar lines — append, don't reorder.

## `bats/fetch-news.bat` (NEW — owner F178-T07)
Follow `bats/process-queue.bat` exactly:
```bat
@echo off
REM ============================================================
REM  fetch-news.bat — Coleta noticias MTG (RSS/Atom) e grava no Neon
REM  Sugestao: Windows Task Scheduler 1x/dia (ex.: 08:00)
REM  Usa DATABASE_URL do .env (carregado por src/config.py)
REM ============================================================

cd /d "%~dp0\.."

echo ============================================================
echo  TEDHC Fetch News - %date% %time%
echo ============================================================

python -m src.cli.main fetch-news --max-per-source 30
if errorlevel 1 (
    echo  [FAIL] Nenhuma fonte de noticias respondeu.
) else (
    echo  [DONE] %date% %time%
)
echo ============================================================
```
CRLF line endings are NOT required (process-queue.bat is LF in repo) — match it.

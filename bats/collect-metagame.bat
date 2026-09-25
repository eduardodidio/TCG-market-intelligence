@echo off
REM ============================================================
REM  collect-metagame.bat — Coleta top decks do metagame (F173)
REM  Fontes: EDHREC (Commander) e MTGTop8 (demais formatos).
REM  Ver docs/adr/0016-metagame-deck-sources.md.
REM
REM  Agendar semanalmente (Task Scheduler, segunda 06:00); diario opcional.
REM
REM  O .env na raiz do repo e carregado automaticamente por
REM  src/config.py (DATABASE_URL -> escreve direto no Neon).
REM  Cache HTTP em data/cache/ (use --no-cache para ignorar).
REM ============================================================

cd /d "%~dp0\.."

echo ============================================================
echo  TEDHC Collect Metagame - %date% %time%
echo ============================================================

python -m src.cli.main collect-metagame --limit 20

echo.
echo  [DONE] %date% %time%
echo ============================================================

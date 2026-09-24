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

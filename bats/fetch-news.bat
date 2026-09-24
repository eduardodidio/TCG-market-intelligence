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

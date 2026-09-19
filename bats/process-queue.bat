@echo off
REM ============================================================
REM  process-queue.bat — Processa fila de solicitacoes de preco
REM  Antigo cron: Windows Task Scheduler as 14:00 e 17:00
REM ============================================================

cd /d "%~dp0\.."

echo ============================================================
echo  TEDHC Process Queue - %date% %time%
echo ============================================================

python -m src.cli.main process-price-requests --limit 100

echo.
echo  [DONE] %date% %time%
echo ============================================================

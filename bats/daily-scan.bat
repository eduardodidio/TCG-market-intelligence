@echo off
REM ============================================================
REM  daily-scan.bat — Liga sweep + process queue + portfolio snapshot
REM  Antigo cron: Windows Task Scheduler as 09:00 diariamente
REM ============================================================

cd /d "%~dp0\.."

echo ============================================================
echo  TEDHC Daily Scan - %date% %time%
echo ============================================================

echo  [%time%] Starting Liga sweep...
python -m src.cli.main liga-sweep --max-age-days 1 || echo  [WARN] liga-sweep failed

echo  [%time%] Processing price request queue...
python -m src.cli.main process-price-requests --limit 500 || echo  [WARN] process-price-requests failed
echo  [%time%] Price request queue done.

echo  [%time%] Taking portfolio snapshot...
python -m src.cli.main snapshot-portfolio || echo  [WARN] snapshot-portfolio failed

echo.
echo  [DONE] %date% %time%
echo ============================================================

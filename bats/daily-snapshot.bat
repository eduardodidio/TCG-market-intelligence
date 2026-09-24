@echo off
REM ============================================================
REM  daily-snapshot.bat — Grava 1 ponto diario de historico por card
REM  (carry-forward ate 30 dias apos a ultima coleta real). Idempotente.
REM  Agendar: Windows Task Scheduler 1x/dia (ex.: 23:30)
REM ============================================================
cd /d "%~dp0\.."
echo  TEDHC Daily Snapshot - %date% %time%
python -m src.cli.main daily-snapshot
echo  [DONE] %date% %time%

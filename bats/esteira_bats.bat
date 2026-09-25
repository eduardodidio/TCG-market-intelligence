@echo off
REM ============================================================
REM  esteira_bats.bat — Executa todos os bats em sequencia
REM  Ordem: banlist-sync, fetch-news, collect-metagame,
REM         daily-scan, process-queue, daily-snapshot,
REM         deck-suggestions
REM  push-all.bat nao e incluido (manual, requer supervisao)
REM ============================================================

cd /d "%~dp0\.."

echo ============================================================
echo  TEDHC Esteira Completa - %date% %time%
echo ============================================================
echo.

echo  [1/7] Banlist Sync...
call bats\banlist-sync.bat
echo.

echo  [2/7] Fetch News...
call bats\fetch-news.bat
echo.

echo  [3/7] Collect Metagame...
call bats\collect-metagame.bat
echo.

echo  [4/7] Daily Scan (liga-sweep + process-queue + snapshot)...
call bats\daily-scan.bat
echo.

echo  [5/7] Process Queue (extra round)...
call bats\process-queue.bat
echo.

echo  [6/7] Daily Snapshot...
call bats\daily-snapshot.bat
echo.

echo  [7/7] Deck Suggestions...
call bats\deck-suggestions.bat
echo.

echo ============================================================
echo  ESTEIRA COMPLETA - %date% %time%
echo ============================================================
pause

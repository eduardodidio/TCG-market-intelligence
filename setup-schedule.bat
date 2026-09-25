@echo off
REM ============================================================
REM  setup-schedule.bat — Agenda tarefas no Task Scheduler
REM  Execute como Administrador
REM ============================================================

echo.
echo Configurando agendamentos TEDHC...
echo.

REM --- Remover todas as tarefas existentes (clean slate) ---
schtasks /delete /tn "TEDHC_DailyScan" /f >nul 2>&1
schtasks /delete /tn "TEDHC_ProcessQueue_14h" /f >nul 2>&1
schtasks /delete /tn "TEDHC_ProcessQueue_17h" /f >nul 2>&1
schtasks /delete /tn "TEDHC_ProcessQueue_18h" /f >nul 2>&1
schtasks /delete /tn "TEDHC_PushAll" /f >nul 2>&1
schtasks /delete /tn "TEDHC_BanlistSync" /f >nul 2>&1
schtasks /delete /tn "TEDHC_CollectMetagame" /f >nul 2>&1
schtasks /delete /tn "TEDHC_DailySnapshot" /f >nul 2>&1
schtasks /delete /tn "TEDHC_DeckSuggestions" /f >nul 2>&1
schtasks /delete /tn "TEDHC_FetchNews" /f >nul 2>&1

echo Tarefas antigas removidas.
echo.

REM --- Deck Suggestions: 03:00 daily ---
schtasks /create /tn "TEDHC_DeckSuggestions" /tr "%~dp0bats\deck-suggestions.bat" /sc daily /st 03:00 /f
if %ERRORLEVEL% EQU 0 (
    echo [OK] TEDHC_DeckSuggestions     — 03:00 diario  ^(sugestoes de decks^)
) else (
    echo [ERRO] Falha ao criar TEDHC_DeckSuggestions
)

REM --- Banlist Sync: 06:00 weekly (Monday) ---
schtasks /create /tn "TEDHC_BanlistSync" /tr "%~dp0bats\banlist-sync.bat" /sc weekly /d MON /st 06:00 /f
if %ERRORLEVEL% EQU 0 (
    echo [OK] TEDHC_BanlistSync         — 06:00 segunda ^(sync banlist^)
) else (
    echo [ERRO] Falha ao criar TEDHC_BanlistSync
)

REM --- Collect Metagame: 06:30 weekly (Monday) ---
schtasks /create /tn "TEDHC_CollectMetagame" /tr "%~dp0bats\collect-metagame.bat" /sc weekly /d MON /st 06:30 /f
if %ERRORLEVEL% EQU 0 (
    echo [OK] TEDHC_CollectMetagame     — 06:30 segunda ^(coleta metagame^)
) else (
    echo [ERRO] Falha ao criar TEDHC_CollectMetagame
)

REM --- Fetch News: 08:00 daily ---
schtasks /create /tn "TEDHC_FetchNews" /tr "%~dp0bats\fetch-news.bat" /sc daily /st 08:00 /f
if %ERRORLEVEL% EQU 0 (
    echo [OK] TEDHC_FetchNews           — 08:00 diario  ^(busca noticias^)
) else (
    echo [ERRO] Falha ao criar TEDHC_FetchNews
)

REM --- Daily Scan: 09:00 daily (liga sweep + process queue + snapshot) ---
schtasks /create /tn "TEDHC_DailyScan" /tr "%~dp0bats\daily-scan.bat" /sc daily /st 09:00 /f
if %ERRORLEVEL% EQU 0 (
    echo [OK] TEDHC_DailyScan           — 09:00 diario  ^(liga sweep + fila + snapshot^)
) else (
    echo [ERRO] Falha ao criar TEDHC_DailyScan
)

REM --- Process Queue 14h: fila de solicitacoes ---
schtasks /create /tn "TEDHC_ProcessQueue_14h" /tr "%~dp0bats\process-queue.bat" /sc daily /st 14:00 /f
if %ERRORLEVEL% EQU 0 (
    echo [OK] TEDHC_ProcessQueue_14h    — 14:00 diario  ^(fila de solicitacoes^)
) else (
    echo [ERRO] Falha ao criar TEDHC_ProcessQueue_14h
)

REM --- Process Queue 17h: fila de solicitacoes ---
schtasks /create /tn "TEDHC_ProcessQueue_17h" /tr "%~dp0bats\process-queue.bat" /sc daily /st 17:00 /f
if %ERRORLEVEL% EQU 0 (
    echo [OK] TEDHC_ProcessQueue_17h    — 17:00 diario  ^(fila de solicitacoes^)
) else (
    echo [ERRO] Falha ao criar TEDHC_ProcessQueue_17h
)

REM --- Daily Snapshot: 23:30 daily ---
schtasks /create /tn "TEDHC_DailySnapshot" /tr "%~dp0bats\daily-snapshot.bat" /sc daily /st 23:30 /f
if %ERRORLEVEL% EQU 0 (
    echo [OK] TEDHC_DailySnapshot       — 23:30 diario  ^(snapshot de precos^)
) else (
    echo [ERRO] Falha ao criar TEDHC_DailySnapshot
)

echo.
echo ============================================================
echo  Resumo dos agendamentos (8 tarefas):
echo.
echo  DIARIAS:
echo    03:00  Deck Suggestions   (sugestoes de decks)
echo    08:00  Fetch News         (busca noticias)
echo    09:00  Daily Scan         (sweep + fila + snapshot)
echo    14:00  Process Queue      (fila de solicitacoes)
echo    17:00  Process Queue      (fila de solicitacoes)
echo    23:30  Daily Snapshot     (snapshot de precos)
echo.
echo  SEMANAIS (segunda-feira):
echo    06:00  Banlist Sync       (sync banlist)
echo    06:30  Collect Metagame   (coleta metagame)
echo.
echo  MANUAL (nao agendado):
echo    --:--  Push All           (push-all.bat, executar manualmente)
echo ============================================================
echo.
pause

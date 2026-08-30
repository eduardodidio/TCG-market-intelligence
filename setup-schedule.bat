@echo off
REM ============================================================
REM  setup-schedule.bat — Agenda push-all.bat no Task Scheduler
REM  Roda diariamente as 08:00
REM  Execute como Administrador se necessario
REM ============================================================

REM Remover tarefa existente (ignora erro se nao existir)
schtasks /delete /tn "TEDHC_PushAll" /f >nul 2>&1

REM Criar tarefa agendada
schtasks /create /tn "TEDHC_PushAll" /tr "C:\Workspace\TCG-market-intelligence\push-all.bat" /sc daily /st 08:00 /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Tarefa "TEDHC_PushAll" agendada para rodar todo dia as 08:00.
    echo     Para alterar o horario, edite este arquivo ou use o Task Scheduler.
) else (
    echo.
    echo [ERRO] Falha ao criar tarefa. Tente rodar como Administrador.
)

echo.
pause

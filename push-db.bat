@echo off
REM ============================================================
REM  push-db.bat — Envia o banco SQLite local para o Render
REM  Usa apos Render restart para restaurar dados da colecao
REM ============================================================

REM --- Configuracao ---
SET REMOTE=https://tcg-market-intelligence.onrender.com

REM API key: defina a variavel de ambiente TCG_API_KEY antes de rodar,
REM ou descomente a linha abaixo e coloque sua chave:
REM SET TCG_API_KEY=sua-chave-aqui

REM --- Validacao ---
if "%TCG_API_KEY%"=="" (
    echo [ERRO] Variavel TCG_API_KEY nao definida.
    echo   Defina com: set TCG_API_KEY=sua-chave
    echo   Ou edite este arquivo e descomente a linha SET TCG_API_KEY=...
    pause
    exit /b 1
)

echo ============================================================
echo  TEDHC Push DB - %date% %time%
echo  Remote: %REMOTE%
echo ============================================================
echo.

REM --- Executa o comando ---
python -m src.cli.main push-db ^
    --remote %REMOTE% ^
    --api-key %TCG_API_KEY%

echo.
if %ERRORLEVEL% EQU 0 (
    echo [OK] Push DB concluido com sucesso!
) else (
    echo [ERRO] Push DB falhou com codigo %ERRORLEVEL%
)

echo.
pause

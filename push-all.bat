@echo off
REM ============================================================
REM  push-all.bat — Envia banco + atualiza precos no Render
REM  1) push-db:     envia o SQLite local para o Render
REM  2) push-prices: escaneia precos via Liga e envia pro Render
REM ============================================================

REM --- Configuracao ---
SET REMOTE=https://tcg-market-intelligence.onrender.com
SET DELAY=5
SET MAX_AGE_DAYS=1

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
echo  TEDHC Push All - %date% %time%
echo  Remote: %REMOTE%
echo ============================================================

REM --- Etapa 1: Push DB ---
echo.
echo [1/2] Enviando banco de dados local para o Render...
echo.

python -m src.cli.main push-db ^
    --remote %REMOTE% ^
    --api-key %TCG_API_KEY%

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Push DB falhou. Abortando.
    pause
    exit /b 1
)

echo.
echo [OK] Banco enviado com sucesso!

REM --- Etapa 2: Push Prices ---
echo.
echo [2/2] Escaneando precos via Liga e enviando para o Render...
echo     Delay: %DELAY%s entre requests
echo     Max age: %MAX_AGE_DAYS% dia(s)
echo.

python -m src.cli.main push-prices ^
    --remote %REMOTE% ^
    --api-key %TCG_API_KEY% ^
    --delay %DELAY% ^
    --max-age-days %MAX_AGE_DAYS%

echo.
if %ERRORLEVEL% EQU 0 (
    echo ============================================================
    echo  [OK] Push All concluido com sucesso!
    echo ============================================================
) else (
    echo [ERRO] Push Prices falhou com codigo %ERRORLEVEL%
)

echo.
pause

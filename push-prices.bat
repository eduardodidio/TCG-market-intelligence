@echo off
REM ============================================================
REM  push-prices.bat — Atualiza precos da colecao no Render
REM  Escaneia via LigaMagic local e envia para o deploy remoto
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
echo  TEDHC Push Prices - %date% %time%
echo  Remote: %REMOTE%
echo  Delay:  %DELAY%s entre requests
echo  Max age: %MAX_AGE_DAYS% dia(s) (pula cards escaneados recentemente)
echo ============================================================
echo.

REM --- Executa o comando ---
python -m src.cli.main push-prices ^
    --remote %REMOTE% ^
    --api-key %TCG_API_KEY% ^
    --delay %DELAY% ^
    --max-age-days %MAX_AGE_DAYS%

echo.
if %ERRORLEVEL% EQU 0 (
    echo [OK] Push concluido com sucesso!
) else (
    echo [ERRO] Push falhou com codigo %ERRORLEVEL%
)

echo.
pause

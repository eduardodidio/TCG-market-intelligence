@echo off
REM ============================================================
REM  push-all.bat — Atualiza precos da colecao no Neon
REM  Conecta direto ao Neon via DATABASE_URL no .env
REM  Fonte: MYP Cards (curl_cffi, sem Cloudflare)
REM  Liga Magic desativada (Cloudflare Turnstile interativo)
REM ============================================================

REM --- Diretorio do projeto ---
cd /d "%~dp0\.."

echo ============================================================
echo  TEDHC Price Update - %date% %time%
echo  (MYP Cards via curl_cffi - escrita direta no Neon)
echo ============================================================
echo.

python -m src.cli.main myp-sweep --max-age-days 1

echo.
if %ERRORLEVEL% EQU 0 (
    echo ============================================================
    echo  [OK] Precos atualizados com sucesso!
    echo ============================================================
) else (
    echo [ERRO] MYP sweep falhou com codigo %ERRORLEVEL%
)

echo.
pause

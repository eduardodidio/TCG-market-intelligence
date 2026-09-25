@echo off
REM ============================================================
REM  push-all.bat — Atualiza precos da colecao no Neon
REM  Conecta direto ao Neon via DATABASE_URL no .env
REM  (push-db e push-prices removidos — escrita direta)
REM ============================================================

REM --- Diretorio do projeto ---
cd /d "%~dp0\.."

echo ============================================================
echo  TEDHC Price Update - %date% %time%
echo  (Escrita direta no Neon via DATABASE_URL)
echo ============================================================
echo.

python -m src.cli.main liga-sweep --max-age-days 1

echo.
if %ERRORLEVEL% EQU 0 (
    echo ============================================================
    echo  [OK] Precos atualizados com sucesso!
    echo ============================================================
) else (
    echo [ERRO] Liga sweep falhou com codigo %ERRORLEVEL%
)

echo.
pause

@echo off
REM ============================================================
REM  deck-suggestions.bat — Processa fila de sugestoes de deck (F172)
REM  Chama o Claude localmente para montar os decks pedidos no site.
REM
REM  Agendamento: Windows Task Scheduler, gatilho diario as 03:00.
REM
REM  Configuracao: o .env na raiz do repo e carregado automaticamente
REM  por src/config.py (DATABASE_URL + variaveis abaixo):
REM    DECK_SUGGEST_PROVIDER    cli (claude -p, padrao) ou api
REM    DECK_SUGGEST_CLAUDE_BIN  binario do Claude CLI (padrao: claude)
REM    DECK_SUGGEST_MODEL       modelo (ex.: claude-sonnet-5)
REM    DECK_SUGGEST_TIMEOUT     timeout por pedido em segundos (padrao: 300)
REM    ANTHROPIC_API_KEY        SOMENTE quando DECK_SUGGEST_PROVIDER=api;
REM                             coloque APENAS no .env, nunca neste arquivo.
REM ============================================================

cd /d "%~dp0\.."

echo ============================================================
echo  TEDHC Deck Suggestions - %date% %time%
echo ============================================================

python -m src.cli.main process-deck-suggestions --limit 10

echo.
echo  [DONE] %date% %time%
echo ============================================================

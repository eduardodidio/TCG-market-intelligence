# F178 — Diagnosis (root causes found during planning)

Findings from repo inspection on 2026-09-24 (branch at `e60ccc8`):

| # | Hipótese do brief | Resultado | Evidência |
|---|---|---|---|
| 1 | Persistência | **OK** — `NewsItemRow` / `UserNewsReadRow` existem; `Repository.upsert_news_item` deduplica por `source_url`. | `src/database/models.py:634-666`, `src/database/repository.py:5075+` |
| 2 | Cron inexistente | **CONFIRMADO** — nada chama `fetch_news` além do CLI. Sem job no APScheduler, sem `.bat`. `bats/` tem só `process-queue.bat`. | `grep -rn fetch_news src/` |
| 3 | Dependência / parsing | **CONFIRMADO (bloqueante)** — `news_fetcher.py` faz `import feedparser` no topo, mas `feedparser` **não está** em `pyproject.toml`. `python -m src.cli.main fetch-news` → `ModuleNotFoundError`. `tests/services/test_news_fetcher.py` também falha na importação em ambiente limpo. | `pyproject.toml` `[project].dependencies` |
| 4 | Fontes RSS | **SUSPEITO** — `https://magic.wizards.com/en/rss/rss.xml` é da era pré-redesign (2023) da Wizards; `https://scryfall.com/blog/rss` não foi verificada. `feedparser.parse(url)` usa o User-Agent padrão do urllib, sem timeout (alguns CDNs retornam 403/travam). Não foi possível verificar do sandbox (proxy bloqueia; ver T08). | `src/services/news_fetcher.py:19-28` |
| 5 | Bloqueio de rede no Render | **Não aplicável após o F178** — as rotas de news no Render só leem do Neon; a coleta roda localmente. | decisão (ver ADR) |
| 6 | UI | **Parcial** — um único `EmptyState` genérico para "banco vazio" **e** "filtro Não lidas vazio" (a aba padrão é `unread`); nenhum sinal de frescor. | `frontend/src/pages/NewsPage.tsx:163-170` |

Conclusão: a tabela está vazia porque o único caminho de escrita (`fetch-news`)
quebra na importação e nunca está agendado. Corrigir o caminho de escrita
(sem feedparser), adicionar uma rotina `.bat` e deixar a UI honesta sobre os
estados.

# PRD: News collection via local .bat routine

**Feature ID:** F178
**Status:** in-progress
**Owner:** @eduardorutkoskididio
**Date:** 2026-09-24
**Branch:** `claude/stoic-mccarthy-nv2690` (batch worktree branch, not `main`)

## Problem

A página de Notícias (F166 — `frontend/src/pages/NewsPage.tsx`,
`src/api/routers/news.py`, `src/services/news_fetcher.py`) sempre mostra o
estado vazio. O endpoint `GET /api/v1/news` apenas lê a tabela `news_items`,
e essa tabela nunca é populada: não existe rotina agendada, e o comando CLI
`fetch-news` existente quebra na importação porque `feedparser` nunca foi
declarado em `pyproject.toml`. Além disso, as URLs de feed configuradas não
foram validadas desde o F166 (a URL da Wizards é da era pré-2023) e a UI não
distingue entre "nada foi coletado", "você já leu tudo" e "erro".

### Diagnosis (root causes found during planning, branch at `e60ccc8`)

| # | Hipótese do brief | Resultado | Evidência |
|---|---|---|---|
| 1 | Persistência | **OK** — `NewsItemRow` / `UserNewsReadRow` existem; `Repository.upsert_news_item` deduplica por `source_url`. | `src/database/models.py:634-666`, `src/database/repository.py:5075+` |
| 2 | Cron inexistente | **CONFIRMADO** — nada chama `fetch_news` além do CLI. Sem job no APScheduler, sem `.bat`. `bats/` tem só `process-queue.bat`. | `grep -rn fetch_news src/` |
| 3 | Dependência / parsing | **CONFIRMADO (bloqueante)** — `news_fetcher.py` faz `import feedparser` no topo, mas `feedparser` **não está** em `pyproject.toml`. `python -m src.cli.main fetch-news` → `ModuleNotFoundError`. `tests/services/test_news_fetcher.py` também falha na importação em ambiente limpo. | `pyproject.toml` `[project].dependencies` |
| 4 | Fontes RSS | **SUSPEITO** — `https://magic.wizards.com/en/rss/rss.xml` é da era pré-redesign (2023) da Wizards; `https://scryfall.com/blog/rss` não foi verificada. `feedparser.parse(url)` usa o User-Agent padrão do urllib, sem timeout (alguns CDNs retornam 403/travam). Não foi possível verificar do sandbox (proxy bloqueia; ver T08). | `src/services/news_fetcher.py:19-28` |
| 5 | Bloqueio de rede no Render | **Não aplicável após o F178** — as rotas de news no Render só leem do Neon; a coleta roda localmente. | decisão (ver ADR) |
| 6 | UI | **Parcial** — um único `EmptyState` genérico para "banco vazio" **e** "filtro Não lidas vazio" (a aba padrão é `unread`); nenhum sinal de frescor. | `frontend/src/pages/NewsPage.tsx:163-170` |

Conclusão: a tabela está vazia porque o único caminho de escrita
(`fetch-news`) quebra na importação e nunca está agendado. Corrigir o
caminho de escrita (sem `feedparser`), adicionar uma rotina `.bat` e deixar
a UI honesta sobre os estados.

## Goal

Rodando `bats/fetch-news.bat` na máquina do usuário, a tabela `news_items`
é populada a partir de fontes RSS/Atom válidas sem depender de
`feedparser`, e a página de Notícias reflete corretamente os estados de
vazio, filtro vazio, erro e desatualizado.

## Scope

### In scope

- Reescrever a camada de fetch do `news_fetcher` com `httpx` (já é
  dependência) + parser RSS/Atom da stdlib (`xml.etree.ElementTree`),
  removendo a dependência não declarada de `feedparser`.
- Lista de fontes validada, com relatório por fonte (status HTTP,
  contagem de itens, erro).
- Novo módulo CLI `src/cli/news_cmd.py` (`fetch-news`, com
  `--check-sources` para dry-run) registrado em `main.py`, substituindo
  o comando inline antigo.
- Novo `bats/fetch-news.bat` (roda localmente no Windows e grava no Neon
  via `DATABASE_URL` do `.env`).
- Novo endpoint `GET /api/v1/news/status` (contagem total + data da
  última notícia coletada) para a UI mostrar o frescor dos dados. O
  endpoint continua **somente leitura** do banco.
- Estados de vazio/erro/desatualizado claros na UI.
- Docs: PRD, ADR, 2 diagramas (`F178-architecture.mmd`,
  `F178-journey.mmd`), atualização do README.

### Out of scope

- Agendamento no servidor (APScheduler/cron no Render). A coleta roda
  localmente, como `process-queue.bat`.
- Tabela nova de execuções (evita editar `src/database/models.py`,
  arquivo compartilhado de alto risco no lote F171–F179).
- Tradução do conteúdo das notícias.

## User flows

Ver `docs/diagrams/F178-architecture.mmd` (component/data-flow) e
`docs/diagrams/F178-journey.mmd` (fluxo do usuário), entregues na Wave
de diagramas (T06).

## Success metrics

- `fetch-news` roda sem `feedparser` instalado e popula `news_items`
  (AC1).
- `fetch-news --check-sources` gera relatório sem escrever no banco
  (AC2).
- Código de saída não-zero quando todas as fontes falham (AC3).
- `GET /api/v1/news/status` retorna `{total_items, last_fetched_at,
  newest_published_at}` (AC5).
- Rotas de news nunca fazem chamadas de rede (AC6).
- UI mostra três estados distintos (banco vazio, filtro vazio, erro) e
  uma dica de desatualizado (AC7).
- Cobertura de testes: happy path, edge cases (enclosure, media:content,
  media:thumbnail, content:encoded, item sem link, data inválida,
  offset não-UTC) e erro (XML inválido) via
  `tests/fixtures/news/*.xml`.

## Open questions

- Nenhuma no momento — fontes padrão serão validadas ao vivo pelo
  usuário (AC9, T08).

## Live validation log

_(a preencher pelo usuário em T08 — validação ao vivo das fontes RSS/Atom
fora do sandbox de nuvem)_

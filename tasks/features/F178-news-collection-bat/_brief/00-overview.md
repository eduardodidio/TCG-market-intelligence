# F178 — Overview: Notícias não carregam (coleta via rotina .bat)

## Problem statement

A página de Notícias (F166 — `frontend/src/pages/NewsPage.tsx`,
`src/api/routers/news.py`, `src/services/news_fetcher.py`) sempre mostra o
estado vazio. O endpoint `GET /api/v1/news` apenas lê a tabela `news_items`,
e essa tabela nunca é populada: não existe rotina agendada, e o comando CLI
`fetch-news` existente quebra na importação porque `feedparser` nunca foi
declarado em `pyproject.toml`. Além disso, as URLs de feed configuradas não
foram validadas desde o F166 (a URL da Wizards é da era pré-2023) e a UI não
distingue entre "nada foi coletado", "você já leu tudo" e "erro".

## Scope

1. Reescrever a camada de fetch do `news_fetcher` com `httpx` (já é
   dependência) + parser RSS/Atom da stdlib (`xml.etree.ElementTree`), para
   remover a dependência não declarada de `feedparser`. **Nenhuma dependência
   nova.**
2. Lista de fontes validada, com relatório por fonte (status HTTP, contagem de
   itens, erro).
3. Novo módulo CLI `src/cli/news_cmd.py` (`fetch-news`, com `--check-sources`
   para dry-run) registrado em `main.py` com uma linha, substituindo o comando
   inline antigo.
4. Novo `bats/fetch-news.bat` (roda localmente no Windows e grava no Neon via
   `DATABASE_URL` do `.env`).
5. O endpoint continua **somente leitura** do banco. Novo endpoint
   `GET /api/v1/news/status` (contagem total + data da última notícia coletada)
   para a UI mostrar o frescor dos dados.
6. Estados de vazio/erro/desatualizado claros na UI.
7. Docs: PRD, ADR, 2 diagramas, atualização do README.

## Out of scope

- Agendamento no servidor (APScheduler/cron no Render). A coleta roda
  localmente, como `process-queue.bat`.
- Tabela nova de execuções (evita editar `src/database/models.py`, arquivo
  compartilhado de alto risco no lote F171–F179).
- Tradução do conteúdo das notícias.

## Constraints

- Lote F171–F179 roda em paralelo. Arquivos compartilhados de alto risco
  (`src/cli/main.py`, `bats/`, `README.md`, `src/api/app.py`,
  `src/database/models.py`, `frontend/src/App.tsx`, `Layout.tsx`) são tocados
  **somente** na última Wave de implementação (F178-T07). O F178 **não** toca
  `app.py`, `models.py`, `App.tsx` nem `Layout.tsx` (o router de news e a rota
  `/news` já estão registrados).
- Sem dependências novas (`httpx` e `click` já estão no `pyproject.toml`).
- Gitflow: o trabalho acontece na `homol`, nunca direto na `main`.
- O sandbox de nuvem bloqueia HTTP de saída (proxy 403 para feeds externos). A
  validação ao vivo das fontes precisa rodar na máquina do usuário (F178-T08).

## Acceptance criteria (titles — details in component shards)

- AC1 — O comando `fetch-news` roda sem `feedparser` instalado e popula `news_items`.
- AC2 — `fetch-news --check-sources` gera um relatório por fonte sem escrever no banco.
- AC3 — O comando sai com código diferente de zero quando **todas** as fontes falham.
- AC4 — `bats/fetch-news.bat` existe e segue o padrão de `bats/process-queue.bat`.
- AC5 — `GET /api/v1/news/status` retorna `{total_items, last_fetched_at, newest_published_at}`.
- AC6 — As rotas de news nunca fazem chamadas de rede (somente leitura).
- AC7 — A UI mostra três estados distintos: banco vazio, filtro vazio e erro; além de uma dica de "desatualizado".
- AC8 — PRD, ADR, `F178-architecture.mmd`, `F178-journey.mmd` e o README entregues.
- AC9 — As fontes padrão foram validadas ao vivo pelo usuário; as fontes quebradas foram removidas.

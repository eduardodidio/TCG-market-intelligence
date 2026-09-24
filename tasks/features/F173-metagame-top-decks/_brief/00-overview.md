# F173 — Top Decks do mercado por formato — Overview

## Problem
A seção Top Decks (`/decks/ranking`, `frontend/src/pages/TopDecksPage.tsx`,
`frontend/src/components/TopDecksPreview.tsx`) hoje só ranqueia os decks **do próprio
usuário** por valor (`GET /api/v1/decks/ranking`, `src/api/routers/decks.py`). O usuário
quer ver os top decks do **mercado/metagame** por formato (Commander, Standard, Pioneer,
Modern, Legacy, Pauper, Vintage), com a decklist, a posição no meta e a data da coleta,
o **valor do deck em BRL** usando os preços que já temos, e o **% que ele já possui** na
coleção.

## Scope
1. SPIKE de fontes (EDHREC p/ Commander; MTGTop8 / MTGGoldfish / mtgdecks p/ construídos)
   com decisão registrada em ADR.
2. Camada HTTP "educada": robots.txt, rate limit, cache em disco com TTL, User-Agent
   identificado, retry com backoff.
3. Adapters de fonte atrás de um Protocol comum (`MetaSource`).
4. Persistência de snapshots: deck (arquétipo, posição, meta share, data) + cartas.
5. Resolução nome → `cards.id` (reuso de `src/decks/importer._find_card_id`).
6. Coleta via novo comando CLI `collect-metagame` + novo `bats/collect-metagame.bat`
   (agendado semanalmente; diário opcional).
7. API `GET /api/v1/meta-decks*` com filtro por formato, valor BRL e % possuído.
8. UI: aba "Mercado" no TopDecksPage com pills de formato; link no TopDecksPreview.
9. Docs: ADR, PRD, 2 diagramas, README.

## Out of scope
- Histórico/gráfico de evolução do meta (dados ficam guardados por `snapshot_date`,
  UI futura).
- Importar deck do meta para "Meus decks" (follow-up; anotar no PRD).
- Coleta disparada pela API/Render (coleta é só local via .bat, como liga-sweep).

## Constraints
- Respeitar ToS/robots.txt: se a fonte proíbe scraping → não usar (ADR registra).
- Sem novas dependências (usar `httpx`/`curl_cffi`, `beautifulsoup4`, `tenacity`,
  `urllib.robotparser` stdlib — todos já no `pyproject.toml`).
- Lote paralelo F171–F179: arquivos compartilhados só na task final (T15). Ver
  `05-integration-and-conflicts.md`.
- Gitflow: trabalho na branch `homol` (ou worktree derivada dela); nunca push em `main`.
- Testes: `pytest tests/ --cov=src --cov-report=term-missing`; `cd frontend && npm test`;
  `ruff check src/`. Testes backend NUNCA fazem rede real (fixtures HTML/JSON salvas).

## Acceptance criteria (titles)
- AC1 ADR de fontes aceito com matriz ToS/robots e fonte escolhida por formato.
- AC2 `collect-metagame` coleta ≥1 formato construído e Commander, idempotente por dia.
- AC3 Rate limit + cache + robots respeitados (testado).
- AC4 Snapshot persistido com rank, meta share, data, fonte e decklist.
- AC5 `GET /api/v1/meta-decks?format=` retorna decks com `total_value_brl`,
  `priced_pct`, `owned_pct` (quando logado).
- AC6 UI aba "Mercado" com filtro de formato, valor BRL, % possuído, decklist expansível.
- AC7 `bats/collect-metagame.bat` criado.
- AC8 PRD, ADR, `F173-architecture.mmd`, `F173-journey.mmd`, README atualizados.
- AC9 Cobertura ≥ 85% nos módulos novos `src/metagame/*`; ruff limpo.

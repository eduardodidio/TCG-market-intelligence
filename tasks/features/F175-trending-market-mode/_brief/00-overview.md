# F175 — Overview: Tendências de mercado com o filtro "minha coleção" desmarcado

## Problema
Em `/trending` o toggle "Somente minha coleção" já vem marcado (`collectionOnly=true`) e mostra
os dados certos. Ao **desmarcar**, o frontend chama
`GET /api/v1/market/trending/{gainers,losers}` **sem** `collection_only`, e o backend vai
pelo caminho de mercado (`Repository.get_trending_price_data`), que devolve uma lista vazia.
O ticker do Dashboard (`fetchTickerData`, sempre em modo mercado) sofre do mesmo problema.

## Escopo
- Corrigir a query de mercado para que inclua as mesmas fontes de preço que o modo coleção usa
  (Liga sweep `liga_{card_id}`, `liga_{card_id}_foil`, `manual_{card_id}`), com desempenho que
  fique dentro do `statement_timeout` do Neon.
- Parar de guardar no cache (30 min) uma resposta vazia vinda de **erro/timeout** (cache poisoning).
- Testes de regressão nos dois modos (backend + frontend).
- Docs: PRD, diagramas `F175-architecture.mmd` e `F175-journey.mmd`, nota no README.

## Fora do escopo
- Mudar o algoritmo de score (`src/analytics/trending.py`): os filtros de `rank_trending` continuam como estão.
- Novas colunas, migrações ou mudanças em `src/database/models.py`.
- Novas chaves de i18n (os arquivos de locale são compartilhados pelo lote).

## Restrições
- Lote F171–F179 roda em paralelo. Arquivos de alto risco (`README.md`, `App.tsx`, `Layout.tsx`,
  `src/cli/main.py`, `models.py`, `src/api/app.py`, `bats/`): só `README.md` é tocado, numa
  task dedicada na última Wave (T08).
- `src/database/repository.py` é grande e compartilhado: a mudança nele fica limitada a
  **delegar** `get_trending_price_data` para um módulo NOVO (`src/database/trending_queries.py`).
- Nenhuma dependência nova. Sem mudanças de CI. Trabalho na branch `homol` (CLAUDE.md Gitflow).
- Preço Liga = `median_price` do sweep (preço `mid`); `liga_catalog_*` NÃO é o formato do sweep.

## Títulos dos critérios de aceite
- AC1: o modo mercado devolve gainers/losers quando existem observações só do Liga sweep (`liga_{id}`).
- AC2: o modo mercado continua incluindo as observações via `source_cards` (MYP / jsonld_snapshot).
- AC3: o modo coleção (`collection_only=true`) continua igual (sem regressão).
- AC4: um erro ou timeout na query não fica em cache; a próxima requisição tenta de novo.
- AC5: a query de mercado termina em < 12s no Neon para 90d (validada pelo script de diagnóstico).
- AC6: ao desmarcar o toggle, o frontend refaz a busca sem `collection_only` e mostra a lista de mercado.
- AC7: PRD, 2 diagramas e nota no README entregues.

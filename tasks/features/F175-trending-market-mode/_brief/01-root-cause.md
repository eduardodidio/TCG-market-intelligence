# 01 — Análise de causa raiz

## Fluxo atual
Frontend `Trending.tsx` → `TrendingSection` (params: `collection_only="true"` só quando está marcado)
→ `fetchTrending` → `GET /api/v1/market/trending/{gainers|losers}`
→ `src/api/routers/market.py:133/166` → `user_id = user.id if collection_only and user else None`
→ `TrendingService.get_trending(...)` (`src/services/trending.py`)
  - `user_id` preenchido → `repo.get_trending_price_data_for_user(user_id, days)` ✅
  - `user_id is None` → `repo.get_trending_price_data(days)` ❌ vazio
→ `compute_trending_score` + `rank_trending` (`src/analytics/trending.py`) → entradas.

## Causa 1 (principal): a query de mercado não enxerga os preços do Liga sweep
`src/database/repository.py:1070` `get_trending_price_data` só faz
`SourceCardRow JOIN PriceObservationRow ON external_id = source_cards.external_id`.
O Liga sweep grava `price_observations.source='liga'` com `external_id='liga_{card_id}'`
(e `liga_{card_id}_foil`); as entradas manuais usam `manual_{card_id}`. Esses IDs **não têm
linha em `source_cards`** (os source_cards do catálogo usam `liga_catalog_{set}_{num}`).
Resultado: o Liga, que é a fonte de preço dominante e densa (diária), fica de fora. Os cards que
sobram (MYP esparso) não passam em `rank_trending` (`min_observations=3`,
`min_consistency=0.25`) → lista vazia.
`get_trending_price_data_for_user` (linha 1119) já corrigiu isso para o modo coleção no passo 2
("Direct Liga/manual pattern prices"). Por isso o modo coleção funciona.

## Causa 2 (agravante): resposta vazia de erro vai para o cache
`TrendingService.get_trending` captura qualquer exceção (ex.: `statement_timeout` de 8s no Neon
numa varredura do mercado inteiro), usa `price_data = {}` e **mesmo assim** grava
`self._cache[cache_key]` por 30 min. O serviço é singleton (`market.py:get_trending_service`),
então uma única falha deixa o modo mercado vazio para todos durante 30 min.

## Descartadas / a verificar
- Frontend: `useApi` inclui `collectionOnly` nas deps e o param é omitido quando falso → o
  backend usa o default `False`. Parece correto, mas falta teste de regressão (T05).
- Cache key: `scope="all"` vs `user_{id}` → não colide.
- Singleton do `TrendingService` segura o primeiro `Repository`. O engine é compartilhado,
  então é aceitável; não mexer nisso.

## Validação
T02 (script de diagnóstico somente leitura) confirma a hipótese contra o banco real: conta os
cards/observações vindos de cada caminho, mede o tempo e roda o ranking.

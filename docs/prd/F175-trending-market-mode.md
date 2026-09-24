# PRD — F175 Tendências de mercado com o filtro "minha coleção" desmarcado

**Status:** planned · **Data:** 2026-09-24 · **Lote:** F171–F179

## Problema

Em `/trending`, o toggle "Somente minha coleção" vem marcado por padrão
(`collectionOnly=true`) e mostra dados corretos. Ao **desmarcar** o toggle,
o frontend chama `GET /api/v1/market/trending/{gainers,losers}` sem
`collection_only`, o backend segue o caminho de mercado
(`Repository.get_trending_price_data`) e devolve uma lista **vazia**. O
ticker do Dashboard (`fetchTickerData`, sempre em modo mercado) sofre do
mesmo problema. O usuário não consegue ver as tendências do mercado como
um todo — só as do próprio acervo.

## Usuários

Qualquer usuário (autenticado ou não) navegando `/trending` em modo
mercado, e qualquer visitante do Dashboard (ticker sempre em modo mercado).

## Causa raiz

### Causa 1 (principal): a query de mercado não enxerga os preços do Liga sweep
`src/database/repository.py:1070` (`get_trending_price_data`) só faz
`SourceCardRow JOIN PriceObservationRow ON external_id = source_cards.external_id`.
O Liga sweep grava `price_observations.source='liga'` com
`external_id='liga_{card_id}'` (e `liga_{card_id}_foil`); entradas manuais
usam `manual_{card_id}`. Esses IDs não têm linha em `source_cards` (os
`source_cards` do catálogo usam `liga_catalog_{set}_{num}`). Resultado: o
Liga — fonte de preço dominante e diária — fica de fora; os cards que
sobram (MYP esparso) não passam nos filtros de `rank_trending`
(`min_observations=3`, `min_consistency=0.25`) → lista vazia.
`get_trending_price_data_for_user` (linha 1119) já resolve isso para o
modo coleção com um segundo caminho de busca direta por padrão
`liga_`/`manual_`; por isso o modo coleção funciona e o modo mercado não.

### Causa 2 (agravante): resposta vazia de erro vai para o cache
`TrendingService.get_trending` captura qualquer exceção (ex.: um
`statement_timeout` de 8s no Neon ao varrer o mercado inteiro), usa
`price_data = {}` e mesmo assim grava o resultado vazio em
`self._cache[cache_key]` por 30 minutos. O serviço é singleton
(`market.py:get_trending_service`), então uma única falha transitória
deixa o modo mercado vazio para **todos os usuários** durante meia hora.

## Objetivos

- G1: o modo mercado (`collection_only` ausente/`false`) devolve
  gainers/losers usando as mesmas fontes de preço que o modo coleção já usa.
- G2: uma falha/timeout na query de mercado não fica em cache — a próxima
  requisição tenta de novo.
- G3: a query de mercado termina dentro do `statement_timeout` do Neon
  para o período padrão (90 dias).
- G4: o toggle do frontend refaz a busca corretamente ao alternar entre
  os dois modos, sem condição de corrida entre respostas.

## Não-objetivos

- Mudar o algoritmo de score (`compute_trending_score`) ou os filtros de
  `rank_trending` (`src/analytics/trending.py`) — permanecem como estão.
- Novas colunas, migrações ou mudanças em `src/database/models.py`.
- Novas chaves de i18n (arquivos de locale compartilhados pelo lote).
- Novas fontes de preço ou mudanças no algoritmo de coleta (Liga/MYP).

## Solução

- **T03 (backend):** novo módulo `src/database/trending_queries.py` com
  `load_market_trending_prices`, que une (a) o caminho atual via
  `source_cards` e (b) um caminho direto sobre `price_observations` para
  `source IN ('liga', 'manual')`, extraindo o `card_id` com a regex
  `^(?:liga|manual)_(\d+)(?:_foil)?$` (garantindo que `liga_catalog_*`
  nunca seja interpretado como card_id). `Repository.get_trending_price_data`
  passa a delegar para essa função. Timeout de sessão fixado em 12s no
  Postgres (`SET LOCAL statement_timeout`).
- **T04 (backend):** `TrendingService.get_trending` para de gravar no
  cache quando a consulta lança exceção; um resultado vazio mas legítimo
  usa TTL curto (2 min) em vez dos 30 min padrão. Log estruturado
  `trending_computed` registra escopo, direção, período e contagens.
- **T05 (frontend):** testes de regressão cobrindo os dois modos do
  toggle em `Trending.tsx`/`TrendingSection.tsx` (com/sem
  `collection_only`, usuário autenticado/anônimo, e uma resposta lenta da
  coleção que não deve sobrescrever uma resposta de mercado mais rápida).
  Correções mínimas no frontend só se um teste revelar um bug real.

## Critérios de aceite

- **AC1:** o modo mercado devolve gainers/losers quando existem
  observações só do Liga sweep (`liga_{id}`).
- **AC2:** o modo mercado continua incluindo as observações via
  `source_cards` (MYP / jsonld_snapshot).
- **AC3:** o modo coleção (`collection_only=true`) continua igual, sem
  regressão.
- **AC4:** um erro ou timeout na query não fica em cache; a próxima
  requisição tenta de novo.
- **AC5:** a query de mercado termina em menos de 12s no Neon para 90
  dias, validada pelo script de diagnóstico (T02).
- **AC6:** ao desmarcar o toggle, o frontend refaz a busca sem
  `collection_only` e mostra a lista de mercado (sem condição de corrida
  entre as respostas dos dois modos).
- **AC7:** PRD, 2 diagramas (`F175-architecture.mmd`, `F175-journey.mmd`)
  e nota no README entregues.

## Riscos

- **Volume de consulta no Neon:** a busca direta por `liga_`/`manual_`
  varre `price_observations` para o mercado inteiro; sem um filtro
  restritivo isso pode aproximar ou estourar o `statement_timeout`. Mitigado
  pelo índice `ix_price_obs_card_date (source, external_id, observed_at)`,
  pelo corte por `observed_at >= cutoff` e pelo timeout explícito de 12s
  fixado na sessão.
- **Mistura de preço foil/não-foil:** `liga_{id}` e `liga_{id}_foil`
  mapeiam para o mesmo `card_id`; quando ambos existem na mesma data, o
  agregador precisa de uma regra determinística (usar o maior preço) para
  não misturar variantes de forma inconsistente com o que o modo coleção
  já faz.
- **Lote paralelo (F171–F179):** vários arquivos de alto risco
  (`README.md`, `App.tsx`, `Layout.tsx`, `models.py`, `repository.py`,
  `src/api/app.py`) são compartilhados. A mudança em `repository.py`
  fica limitada a delegar para o novo módulo; a nota no `README.md` fica
  isolada na última Wave (T08).

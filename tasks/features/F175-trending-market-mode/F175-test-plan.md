# F175 — Test Plan

- **status:** drafted
- **generator:** TEA
- **generated-at:** 2026-09-24
- **source-brief:** `tasks/features/F175-trending-market-mode/_brief/00-overview.md`

## 1. Fixtures

| Fixture | Path | Domain | Owner |
|---|---|---|---|
| `_sqlite_engine_with_prices` (in-memory SQLite, `Base.metadata.create_all`, seeds `SourceCardRow` + `PriceObservationRow` for `liga_{id}`, `liga_{id}_foil`, `manual_{id}`, `liga_catalog_*`) | `tests/unit/database/test_trending_queries.py` | db | F175-T03 |
| `_mock_repo_raising` (MagicMock repo whose `get_trending_price_data` raises on 1st call, succeeds after) | `tests/unit/services/test_trending_service_cache_f175.py` | api/service | F175-T04 |
| `_mock_repo_empty` (MagicMock repo returning `{}` — legitimate empty result, no exception) | `tests/unit/services/test_trending_service_cache_f175.py` | api/service | F175-T04 |
| `mockTrendingByMode` (mock of `fetchTrending` returning "Owned Card" when `collection_only === "true"`, "Market Card" otherwise; a slow-resolving variant for the race scenario) | `frontend/src/pages/__tests__/TrendingCollectionToggle.test.tsx` | frontend | F175-T05 |
| `_seed_market_and_collection_cards` (real SQLite `Repository`: rising Liga-only card, falling Liga-only card, MYP card via `SourceCardRow`, `UserCollectionRow` owning 1 card, FastAPI `TestClient` with dependency overrides, autouse reset of `market._trending_service`) | `tests/unit/api/test_f175_trending_market_mode.py` | api/db | F175-T07 |
| `sample_price_data` (dict `{card_id: [(date, Decimal)]}` for `summarize()` — happy/empty/boundary cases) | `tests/unit/scripts/test_diagnose_trending_f175.py` | scripts | F175-T02 |

Nenhum fixture é um arquivo de dados estático (JSON/CSV) — todos são builders Python/TS
construídos in-line no arquivo de teste que os usa, seguindo o padrão já existente em
`tests/unit/services/test_trending_service.py` (`_mock_repo`, `_mock_converter`) e
`frontend/src/pages/__tests__/Dashboard.test.tsx`. Não há necessidade de um diretório de
fixtures compartilhado — `feedback_no_ceremony_specs.md`: criar arquivos de fixture separados
aqui só adicionaria indireção sem retrabalho evitado, já que nenhum dos 4 domínios (db, service,
frontend, scripts) reaproveita dados de outro.

## 2. Harnesses por fronteira

### Unit
- **Framework:** pytest (backend) / Vitest (frontend, para a função pura `summarize` não se aplica — é Python).
- **Comando:** `pytest tests/unit/database/test_trending_queries.py tests/unit/services/test_trending_service_cache_f175.py tests/unit/scripts/test_diagnose_trending_f175.py -v`
- **Path padrão:** `tests/unit/**/*.py`

### Integration
- **Framework:** pytest + FastAPI `TestClient` sobre `Repository` real com SQLite in-memory (sem mock de repo, exceto o cenário de injeção de exceção).
- **Comando:** `pytest tests/unit/api/test_f175_trending_market_mode.py -v` e depois `pytest tests/ -k trending`
- **Path padrão:** `tests/unit/api/test_f175_trending_market_mode.py`

### E2E
- **N/A.** O AC6 (toggle refaz a busca) é coberto como teste de componente frontend
  (`TrendingCollectionToggle.test.tsx` com Testing Library + user-event sobre o componente real,
  API mockada), não como E2E de browser real. O projeto não tem harness de E2E (Playwright/Cypress)
  configurado para fluxos de UI neste momento — o Playwright do repo é usado só pelo provider
  Liga Magic (scraping), não para testes de frontend. Justificativa: 1-line — não vale montar um
  harness E2E novo para uma correção de bug isolada num toggle já coberto por teste de componente
  + teste de API real (T07).

## 3. Perf budgets

| Métrica | Limite | Como medir | Aplicável a |
|---|---|---|---|
| Query de mercado (`load_market_trending_prices`), período 90d, Neon (Postgres) | < 12s (statement_timeout) | `scripts/diagnose_trending_f175.py --days 90` (T02), tempo reportado no item 1 do relatório | AC5 / F175-T02, F175-T03 |
| Cache de resultado bem-sucedido | TTL 30 min (sem regressão) | Asserção de tempo em `test_trending_service_cache_f175.py` (patch de `datetime` ou edição do timestamp da entrada, como em `test_cache_miss_after_ttl`) | F175-T04 |
| Cache de resultado vazio legítimo | TTL 2 min | Mesmo mecanismo acima, limite reduzido | F175-T04 |

Sem budget de latência de API (endpoint) além do já coberto pelo timeout de statement — o
escopo da feature é correção de dados, não de performance de rede.

## 4. Mocks vs hits real

| Componente | Decisão | Justificativa |
|---|---|---|
| DB em `test_trending_queries.py` (T03) | real (SQLite in-memory) | A lógica em teste é a query SQL em si (union, dedup por dia, regex de `external_id`); mockar o DB esconderia exatamente o que pode quebrar. Custo de usar SQLite real aqui é baixo (in-memory, sem I/O de disco). |
| `Repository` em `test_f175_trending_market_mode.py` (T07) | híbrido: real por padrão, mock só no cenário de injeção de exceção (AC4) | Regressão real (AC1–AC3) exige DB real ponta a ponta pela API; a única forma barata e determinística de simular timeout/erro de query é substituir o método por um mock que levanta exceção uma vez — `feedback_no_ceremony_specs.md`: um mock aqui evita ter que forçar um timeout real no SQLite, o que seria instável e lento. |
| `Repository` em `test_trending_service_cache_f175.py` (T04) | mock (MagicMock) | `TrendingService` já é testado com repo mockado no arquivo existente (`test_trending_service.py`); o comportamento em teste é a política de cache do serviço, não a query. Repetir o padrão evita reescrever fixtures de DB para uma unidade que não depende delas. |
| `fetchTrending` no frontend (T05) | mock (`vi.mock`) | Teste de componente, não de integração de rede; seguir o padrão já usado em `Dashboard.test.tsx`. Mock determinístico por `params.collection_only` é a forma mais simples de expor a diferença entre os dois modos. |
| `datetime`/relógio em testes de TTL (T04) | mock (patch de `src.services.trending.datetime` ou edição direta do timestamp da entrada de cache) | Testar TTL de 2 min / 30 min com `time.sleep` real tornaria a suíte lenta e flaky; já é o padrão do arquivo existente `test_cache_miss_after_ttl`. |
| Postgres real (`statement_timeout` local) | real, mas só via script manual (T02), não em pytest | AC5 exige medir tempo real no Neon; isso é ambiente-dependente (rede, cold start) e não determinístico o bastante para CI — fica no script de diagnóstico rodado manualmente, não na suíte automatizada. |

## 5. Test scenarios resumo

1. `parse_direct_card_id` cobre `liga_42`, `liga_42_foil`, `manual_42`, `liga_catalog_mh3_12` (ignorado), `liga_abc` (ignorado), `manual_` (ignorado) — **F175-T03**.
2. `load_market_trending_prices`: 5 dias de `liga_42` subindo → série ascendente de 5 pontos — **F175-T03**.
3. `load_market_trending_prices`: source_cards (MYP) + liga para o mesmo card → série mesclada, dedup por dia — **F175-T03**.
4. `load_market_trending_prices`: `liga_42` e `liga_42_foil` no mesmo dia, preços diferentes → vence o maior — **F175-T03**.
5. `load_market_trending_prices`: observação exatamente no cutoff é incluída; `cutoff - 1 dia` é excluída — **F175-T03**.
6. `load_market_trending_prices`: `median_price` NULL é ignorado; DB vazio → `{}` — **F175-T03**.
7. `get_trending_price_data` (delegação): testes existentes do path `source_cards` continuam passando sem alteração — **F175-T03**.
8. `TrendingService.get_trending`: repo levanta exceção na 1ª chamada → resposta vazia; 2ª chamada chama o repo de novo (`call_count == 2`, sem cache) — **F175-T04**.
9. `TrendingService.get_trending`: resultado vazio legítimo é cacheado por ≤ 2 min, recomputado depois — **F175-T04**.
10. `TrendingService.get_trending`: resultado não vazio continua cacheado por 30 min (sem regressão) — **F175-T04**.
11. `TrendingService.get_trending`: falha no cache `scope=all` não contamina o cache `user_{id}` e vice-versa — **F175-T04**.
12. Toggle "minha coleção" desmarcado → `TrendingSection` refaz a busca sem `collection_only` e renderiza "Market Card" nas duas seções (gainers/losers) — **F175-T05**.
13. Toggle desmarcar e marcar de novo → volta a "Owned Card" — **F175-T05**.
14. Modo mercado com `cards: []` → `EmptyState` com `trending.noTrending`, sem crash — **F175-T05**.
15. `fetchTrending` rejeita em modo mercado → `ErrorBanner` com retry funcional — **F175-T05**.
16. Resposta lenta do modo coleção que resolve depois da resposta de mercado não deve sobrescrever a lista já exibida (condição de corrida) — **F175-T05**.
17. `GET /market/trending/gainers|losers` sem `collection_only`, com DB real: card só-Liga aparece (AC1) e card MYP via `source_cards` também aparece (AC2) — **F175-T07**.
18. `collection_only=true` autenticado → só o card do usuário (AC3, sem regressão) — **F175-T07**.
19. Usuário anônimo com `collection_only=true` → cai em modo mercado (comportamento atual do router, sem regressão) — **F175-T07**.
20. Dado só em `liga_catalog_*` sem `source_cards` correspondente → ignorado, não quebra a resposta — **F175-T07**.
21. `period=7d` com pontos de 8 dias atrás → excluídos; `limit=1` → 1 card — **F175-T07**.
22. `period` inválido → 422; repo levanta exceção → 200 com `cards: []`, resposta não cacheada (fim a fim via API) — **F175-T07**.
23. `summarize()` do script de diagnóstico: 3 cards com 1 em alta → contagens corretas; `price_data` vazio → zeros sem exceção; card com exatamente 3 datas (limite `min_observations`) é contado — **F175-T02**.
24. `scripts/diagnose_trending_f175.py --days 0` (ou negativo) → erro de argparse, exit code != 0 — **F175-T02**.
25. `scripts/diagnose_trending_f175.py --days 30` roda sem erro contra SQLite local e não faz nenhuma escrita no DB (revisão manual: só SELECT) — **F175-T02**.

## 6. Anotações para tasks

- (F175-T02, `sample_price_data`)
- (F175-T03, `_sqlite_engine_with_prices`)
- (F175-T04, `_mock_repo_raising`, `_mock_repo_empty`)
- (F175-T05, `mockTrendingByMode`)
- (F175-T07, `_seed_market_and_collection_cards`)

## Riscos para QA

- **Timeout do Neon em produção não é testável por pytest**: AC5 (< 12s no Neon para 90d) só é
  validado pelo script `diagnose_trending_f175.py` rodado manualmente contra o Neon real (T02).
  QA deve rodar esse script contra o ambiente de homologação antes de promover para `main`, não
  apenas confiar na suíte SQLite in-memory (que não reflete latência de rede/pool do Neon).
- **T05 é condicional**: só altera `TrendingSection.tsx`/`useApi.ts` se o teste de corrida
  (cenário 16) revelar um bug real. QA deve conferir a nota de conclusão da T05 para saber se
  houve fix de código além do teste, e se sim, revisar esse diff com atenção redobrada (é o único
  ponto de código de produção no frontend tocado pela feature).
- **Cobertura de `liga_catalog_*` como negativo**: a regex `^(?:liga|manual)_(\d+)(?:_foil)?$`
  é a autoridade final para não confundir `liga_catalog_mh3_12` com um card_id direto. Um erro
  aqui não quebra nenhum teste de schema (roda silenciosamente), então os cenários 1 e 20 acima
  são a única rede de segurança — QA deve confirmar que ambos existem e passam antes do merge.

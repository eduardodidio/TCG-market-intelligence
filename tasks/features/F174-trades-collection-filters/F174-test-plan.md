# F174 — Test Plan

- **status:** drafted
- **generator:** TEA
- **generated-at:** 2026-09-24
- **source-brief:** `tasks/features/F174-trades-collection-filters/_brief/00-overview.md`

## 1. Fixtures

| Fixture | Path | Domain | Owner |
|---|---|---|---|
| `_seed_listings_and_duplicates` (in-memory SQLite `Repository`, seeds `SharedCollectionRow`/`UserCollectionRow`/`CardRow`/`PriceObservationRow` across 2+ sets and 3 users, including a card with no price and a `name_pt` NULL row) | `tests/marketplace/test_trade_queries.py` | db | F174-T03 |
| `_repo_dependency_overrides` (FastAPI `TestClient` + `app.dependency_overrides[get_optional_user]`/`get_current_user`, reusing `_seed_listings_and_duplicates`) | `tests/marketplace/test_router.py`, `tests/api/test_trade_match_router.py` | api | F174-T07, F174-T08 |
| `mixedCardListFixture` (plain TS objects: mixed name/namePt casing, accented names, null set/number/price, a `'10a'` collector number) | `frontend/src/utils/__tests__/cardListFilter.test.ts` | frontend | F174-T04 |
| `mockCardFilterBarProps` (minimal `CardFilterBarProps` builder: search, sortOptions, setOptions, gridSize permutations) | `frontend/src/components/__tests__/CardFilterBar.test.tsx` | frontend | F174-T05 |
| `MemoryRouterWithParams` (`renderHook` + `MemoryRouter initialEntries={[...]}` wrapper for URL-synced state) | `frontend/src/hooks/__tests__/useCardListFilters.test.tsx` | frontend | F174-T05 |
| `tradeFixture` (a `Trade` object builder: seller/buyer role, each status, with/without `counterparty_share_code`) | `frontend/src/components/__tests__/TradeCard.test.tsx` | frontend | F174-T06 |
| `mockListingsPages` (mock of `fetchListings`/`fetchListingSets` returning paged offset/limit responses, plus a slow-resolving variant for the stale-response scenario) | `frontend/src/pages/__tests__/Marketplace.test.tsx` | frontend | F174-T09 |
| `mockMyTradesFixture` (mock of `fetchMyTrades` with 0/1/N trades across both roles and all 5 statuses) | `frontend/src/pages/__tests__/MyTrades.test.tsx` | frontend | F174-T10 |
| `mockDuplicatesAndMatches` (mock of `tradeMatch` API: `fetchDuplicates`, `fetchDuplicateSets`, matches with a partner reduced to 0 cards after filtering) | `frontend/src/pages/__tests__/TradeMatchesPage.test.tsx` | frontend | F174-T11 |

Nenhum fixture é um arquivo de dados estático (JSON/CSV) — todos são builders
Python/TS in-line, seguindo o padrão já existente em
`tests/marketplace/conftest.py` e `tests/api/test_trade_match_router.py`
(backend) e `frontend/src/pages/__tests__/Dashboard.test.tsx` (frontend). Um
único fixture de seed (`_seed_listings_and_duplicates`) é reaproveitado por
T03/T07/T08 porque os três exercitam o mesmo shape de dados (listagens +
duplicatas); criar fixtures separadas por task aqui adicionaria indireção sem
retrabalho evitado — `feedback_no_ceremony_specs.md`.

## 2. Harnesses por fronteira

### Unit
- **Framework:** pytest (backend) / Vitest (frontend).
- **Comando:** `pytest tests/marketplace/test_trade_queries.py -v` e
  `cd frontend && npx vitest run src/utils/__tests__/cardListFilter.test.ts src/components/__tests__/CardFilterBar.test.tsx src/hooks/__tests__/useCardListFilters.test.tsx src/components/__tests__/TradeCard.test.tsx`
- **Path padrão:** `tests/marketplace/*.py`, `frontend/src/{utils,components,hooks}/__tests__/*.{ts,tsx}`

### Integration
- **Framework:** pytest + FastAPI `TestClient` sobre `Repository` real
  (SQLite in-memory), padrão existente em `test_router.py` e
  `test_trade_match_router.py`. No frontend, testes de página com Testing
  Library + API mockada (`vi.mock`), padrão existente em
  `MyCollection.test.tsx`.
- **Comando:** `pytest tests/marketplace tests/api/test_trade_match_router.py -v`
  e `cd frontend && npx vitest run src/pages/__tests__/Marketplace.test.tsx src/pages/__tests__/MyTrades.test.tsx src/pages/__tests__/TradeMatchesPage.test.tsx src/components/__tests__/DuplicatesList.test.tsx`
- **Path padrão:** `tests/marketplace/test_router.py`,
  `tests/api/test_trade_match_router.py`, `frontend/src/pages/__tests__/*.tsx`

### E2E
- **N/A.** O projeto não tem harness de E2E de browser (Playwright/Cypress)
  configurado para fluxos de UI — o Playwright existente é usado só pelo
  provider Liga Magic (scraping), não para testes de frontend. Os fluxos
  ponta a ponta (filtro → fetch → render → URL) são cobertos por testes de
  página com Testing Library + API mockada (T09–T11) e pelos testes de API
  real com SQLite (T07/T08), o que já fecha o caminho request→DB→resposta;
  montar um harness E2E novo só para esta feature não se justifica —
  `feedback_no_ceremony_specs.md`.

## 3. Perf budgets

_Sem perf budgets aplicáveis._ A feature reusa os limites de paginação já
existentes (`limit<=100` em marketplace, `limit<=200` em duplicates) e não
introduz nova query pesada — `TradeQueries` espelha os padrões de índice já
usados por `Repository.list_marketplace_entries`/`get_user_duplicates`. Não
há requisito de latência específico no brief (`_brief/01-backend.md`), então
nenhum budget novo é justificável só por precaução.

## 4. Mocks vs hits real

| Componente | Decisão | Justificativa |
|---|---|---|
| `Repository`/DB em `test_trade_queries.py` (T03) | real (SQLite in-memory) | A lógica em teste é a query SQL em si (WHERE de busca/set, ORDER BY com NULLS last, JOINs de preço); mockar o DB esconderia exatamente o que pode quebrar. Custo de SQLite real in-memory é baixo. |
| `Repository` em `test_router.py`/`test_trade_match_router.py` (T07/T08) | real (via `dependency_overrides`, sem mock de `TradeQueries`) | Já é o padrão dos arquivos existentes; os ACs exigem paridade de payload/ordem com o comportamento atual, o que só uma pilha real ponta a ponta garante. |
| `cardListFilter.ts`/`tradeSortOptions.ts` (T04) | real, sem mock (funções puras) | Não há I/O nem dependência externa — testar com objetos simples é mais barato e mais fiel do que qualquer mock. |
| APIs (`fetchListings`, `fetchListingSets`, `fetchMyTrades`, `tradeMatch.*`) nos testes de página (T09–T11) | mock (`vi.mock`) | Testes de componente/página, não de integração de rede; padrão já usado em `Dashboard.test.tsx`/`MyCollection.test.tsx`. Mockar evita subir um backend real só para testar reatividade de UI a mudanças de filtro. |
| `react-i18next` em todos os testes de componente frontend | mock (`t: k => k`) | Padrão já estabelecido no repo (`CLAUDE.md`/testes existentes); testar strings traduzidas de verdade só adicionaria acoplamento aos JSONs de locale sem valor para a lógica de filtro. |
| `useInfiniteScroll`/`IntersectionObserver` (T09) | mock/stub | JSDOM não implementa `IntersectionObserver`; stub determinístico é necessário para disparar `loadMore` no teste sem depender de layout real. |
| `MemoryRouter`/`useSearchParams` (T05, T09-T11) | real (react-router-dom real, sem mock) | O comportamento em teste é justamente a sincronização com a URL; mockar `useSearchParams` esconderia bugs de codificação/merge de params. Custo de usar o `MemoryRouter` real é desprezível. |

## 5. Test scenarios resumo

1. `TradeQueries.list_listings()` default retorna as mesmas linhas/ordem/keys que `Repository.list_marketplace_entries()` sobre os mesmos dados — **F174-T03**.
2. `TradeQueries.list_duplicates()` default retorna as mesmas linhas/ordem/total que `Repository.get_user_duplicates()` — **F174-T03**.
3. Sort por name/set/number/price asc/desc; preço NULL sempre por último em ambas direções; tiebreaker por `id` mantém ordem determinística — **F174-T03**.
4. Busca por `name_en` OU `name_pt`, case-insensitive; filtro de set case-insensitive; string de busca só com espaços é ignorada — **F174-T03**.
5. `list_listing_sets`/`list_duplicate_sets` retornam `{set_code,set_name,count}`; listings exclui o próprio viewer; duplicates só inclui qty>1 com card_id — **F174-T03**.
6. `sort_by='drop table'` ou `sort_dir='up'` → `ValueError` — **F174-T03**.
7. Paginação `limit`/`offset` determinística e disjunta entre páginas; offset além do total → `[]` — **F174-T03**.
8. `GET /marketplace/listings` sem os novos params retorna o mesmo payload/ordem de hoje; com `sort_by=price&sort_dir=desc` ordena com nulls last — **F174-T07**.
9. `GET /marketplace/listings` com `sort_by=foo` ou `sort_dir=up` → 422 — **F174-T07**.
10. `GET /marketplace/listings/sets` retorna `{sets:[...]}`, não é capturada pela rota `{share_code}`, e exclui os próprios sets do viewer autenticado; anônimo funciona — **F174-T07**.
11. `GET /trade/duplicates` sem novos params mantém items/ordem/total; com `search`+`set_code` filtra e `total` reflete o filtro; sort inválido → 422 — **F174-T08**.
12. `GET /trade/duplicates/sets` exige auth e retorna só sets com qty>1; `search` acima de 100 chars → 422 — **F174-T08**.
13. `filterCardList`/`sortCardList`: busca acento-insensível ('Relâmpago' casa com 'relampago'), sort estável com nulls last e natural sort de coletor ('2' < '10' < '10a') — **F174-T04**.
14. `buildSetOptions`: de-duplicado, values minúsculos, labels maiúsculos, ordenado; array vazio não quebra — **F174-T04**.
15. `sortBy` desconhecido em `sortCardList` → cópia na ordem original, sem mutar o array de entrada — **F174-T04**.
16. `CardFilterBar`: digitar chama `onSearchChange`; escolher sort chama `onSortChange('price','desc')`; clicar num set chama `onSetSelect`; `setOptions=[]` → sem `set-icon-filter`; sem `gridSize` → sem `filter-bar-actions` — **F174-T05**.
17. `useCardListFilters`: inicializa de `?name&set&sort&dir`; `dir` inválido cai no default; troca de sort preserva outros params (`tab`); resetar remove `sort`/`dir`/`name` vazios da URL; `debouncedSearch` só atualiza após 300ms — **F174-T05**.
18. `TradeCard`: seller+pending mostra accept/reject e aciona `onAccept(id)`; buyer+pending não mostra accept/reject; accepted mostra confirm; completed mostra e-mail; `compact` esconde código da contraparte e a linha de taxa — **F174-T06**.
19. `TradeCard`: status desconhecido cai no estilo pending; erro de imagem cai no fallback por nome; handler undefined não lança exceção ao clicar — **F174-T06**.
20. Marketplace: carregar → 40 itens → `loadMore` → 80 itens com `offset=40`; resposta desatualizada de uma busca anterior é ignorada quando uma busca mais nova já resolveu — **F174-T09**.
21. Marketplace: `?search=bolt` na URL semeia a caixa de busca; sets vazios → sem filtro de set; `fetchListings`/`fetchListingSets` rejeitando não quebram a página (ErrorBanner com retry / sem linha de set) — **F174-T09**.
22. MyTrades: busca 'bolt' filtra para 1 tile; chip de status 'pending' isola pendentes; `?tab=seller` na URL seleciona a aba vendedor e persiste após trocar filtro — **F174-T10**.
23. MyTrades: `fetchMyTrades` rejeita → ErrorBanner com retry; `confirmAgreement` com `INSUFFICIENT_CREDITS` → mensagem traduzida; vazio filtrado usa `tradeFilters.noResults`, vazio sem filtro usa a mensagem por papel — **F174-T10**.
24. TradeMatches: digitar busca na aba duplicates chama o fetcher com `search`; trocar para `theyHave` + filtrar por set mostra só thumbnails correspondentes; trocar de aba reseta o sort para o default da aba — **F174-T11**.
25. TradeMatches: todos os parceiros filtrados para 0 cards → `tradeFilters.noResults`; sets vazios → sem linha de set; não autenticado → mensagem de login exigido — **F174-T11**.
26. MyCollection: busca/sort/set continuam a se comportar exatamente como antes após a extração para `CardFilterBar` — provado pelos testes pré-existentes passando **sem modificação** — **F174-T12**.
27. Regressão global: nenhum arquivo de teste frontend novo entra na lista de falhas (baseline de 13 arquivos falhando não pode crescer) — **F174-T09, F174-T10, F174-T11, F174-T12** (verificado por QA no fechamento).

## 6. Anotações para tasks

- (F174-T03, `_seed_listings_and_duplicates`)
- (F174-T04, `mixedCardListFixture`)
- (F174-T05, `mockCardFilterBarProps`, `MemoryRouterWithParams`)
- (F174-T06, `tradeFixture`)
- (F174-T07, `_seed_listings_and_duplicates`, `_repo_dependency_overrides`)
- (F174-T08, `_seed_listings_and_duplicates`, `_repo_dependency_overrides`)
- (F174-T09, `mockListingsPages`)
- (F174-T10, `mockMyTradesFixture`)
- (F174-T11, `mockDuplicatesAndMatches`)

## Riscos para QA

- **Baseline de falhas do frontend é uma linha móvel**: o gate de F174 é "≤13
  arquivos falhando e nenhum nome novo", não "0 falhas". QA deve rodar
  `cd frontend && npm test` **antes** de qualquer task começar (ou usar o
  relatório de readiness já existente) para fixar a lista de 13 nomes, e
  comparar a lista de nomes (não só a contagem) depois de T09–T12, porque uma
  troca 1-por-1 (um teste antigo passa a passar, um novo quebra) manteria a
  contagem em 13 mas seria uma regressão real.
- **T12 é o único guard-rail de não-regressão do MyCollection**: nenhum teste
  de `MyCollection*.test.tsx`/`CollectionCardTile3D.test.tsx` pode ser editado
  por esta feature. QA deve conferir `git diff` desses arquivos == vazio antes
  de aprovar T12, não apenas que os testes passam (um dev sob pressão poderia
  "consertar" um teste quebrado editando-o em vez de corrigir o componente).
- **Route ordering em `/marketplace/listings/sets`** (T07) é testado
  implicitamente por `share_code` aleatórios nunca colidirem com `sets` nos
  fixtures atuais; se algum teste futuro gerar `share_code='sets'`, o teste de
  regressão da rota `{share_code}` pode mascarar um bug real de ordering. QA
  deve confirmar que existe pelo menos um teste explícito de
  `GET /marketplace/listings/sets` retornando `{sets:[...]}` e não um único
  listing (T07, cenário 10 acima).
- **Cobertura ≥90% de `trade_queries.py` (AC8)** depende de exercitar os 4
  branches de sort (name/set/number/price) × 2 direções para listings e
  duplicates — 8 combinações. QA deve rodar
  `pytest tests/marketplace/test_trade_queries.py --cov=src/marketplace --cov-report=term-missing`
  e não confiar apenas no número agregado da suíte completa, que pode
  esconder um branch de sort não coberto se outro módulo compensar a média.

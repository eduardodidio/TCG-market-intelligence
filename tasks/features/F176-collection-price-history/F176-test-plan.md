# F176 — Test Plan

- **status:** drafted
- **generator:** TEA
- **generated-at:** 2026-09-24
- **source-brief:** `tasks/features/F176-collection-price-history/_brief/00-overview.md`

## 1. Fixtures

| Fixture | Path | Domain | Owner |
|---|---|---|---|
| `repo` (SQLite in-memory `Repository("sqlite:///:memory:")` + `Base.metadata.create_all`, sem seed) + `collect_entry_diagnosis`/`summarize` chamados sobre linhas inseridas via `repo.insert_price_observations` | `tests/scripts/test_diagnose_collection_history.py` | scripts | F176-T01 |
| `_fixture_neon_readonly_note` (não é fixture de código — nota manual de que `scripts/diagnose_collection_history_neon.sql` só é validado por execução manual do usuário contra Neon, sem fixture pytest) | `tasks/features/F176-collection-price-history/diagnosis.md` | scripts | F176-T01 |
| `card_id_matrix` (`pytest.mark.parametrize` com a matriz variante × `source_cards`: sem source_cards, MYP normal, MYP `_foil`, catálogo `liga_catalog_*`, duplicados) usada direto em `HistoricalPrice(...)` sem DB | `tests/collection/test_price_history_keys.py` | collection (puro) | F176-T03 |
| `repo` (mesmo padrão de `tests/test_price_snapshot.py`: SQLite in-memory + `_insert_observation` helper) fixado com `today=date(2026, 9, 24)` | `tests/collectors/test_price_snapshot_forward_fill.py`, `tests/test_price_snapshot.py` | collectors | F176-T05 |
| `_mock_provider_search` / `_make_cards` (mesmos helpers de `tests/collectors/test_liga_sweep.py`, reaproveitados) + patch de `src.collectors.price_snapshot.run_daily_snapshot` para os testes que não querem o efeito colateral | `tests/collectors/test_liga_sweep_daily_snapshot.py` | collectors | F176-T06 |
| `repo` com `CardRow`+`SourceCardRow`+`PriceObservationRow` inseridos via `Session(repo.engine)` (padrão de `tests/integration/test_snapshot_pipeline.py::_seed_cards_with_prices`), cobrindo card só-Liga, card com MYP, card foil | `tests/services/test_collection_price_history.py` | services/db | F176-T07 |
| SQLAlchemy event `before_cursor_execute` contando `SELECT`s em `price_observations` (para a AC "uma única query") | `tests/services/test_collection_price_history.py` | services/db | F176-T07 |
| App FastAPI mínimo com `collection_router` + `dependency_overrides` de `get_db`, `require_auth_or_api_key`, `get_currency_converter_dep` (padrão de `tests/api/test_collection_detail.py`) | `tests/api/test_collection_history_resolver.py` | api | F176-T08 |
| App FastAPI mínimo com `cards_router` + override de `get_db` (padrão de `tests/integration/test_snapshot_pipeline.py`) | `tests/api/test_cards_history_resolver.py` | api | F176-T09 |
| `renderWithMeta` (helper local que envolve `PriceHistoryMeta`/`PriceChart` com `I18nextProvider`, seguindo o setup i18n de `AchievementToast.test.tsx`) + mock de `ResponsiveContainer` (padrão já usado em outros testes de gráfico do repo) | `frontend/src/components/__tests__/PriceHistoryMeta.test.tsx`, `frontend/src/components/__tests__/PriceChart.test.tsx` | frontend | F176-T10 |
| `click.testing.CliRunner` + `--db sqlite:///<tmp_path>/t.db` (padrão de `tests/test_cli_snapshot.py`) | `tests/test_cli_snapshot.py` | cli | F176-T11 |
| App FastAPI completo (`collection_router` + `cards_router`) + `Repository(db_url="sqlite:///" + str(tmp_path / "f176.db"))` (arquivo, não in-memory — o sweep abre sua própria engine) + provider Liga fake (patch de construtor, como em `tests/collectors/test_liga_sweep.py`) | `tests/integration/test_collection_price_history.py` | integration | F176-T12 |

Nenhum fixture é arquivo estático (JSON/CSV/imagem). Todos são builders Python/TS
in-line seguindo os padrões já existentes no repo (`_insert_observation` de
`tests/test_price_snapshot.py`, `_seed_cards_with_prices` de
`tests/integration/test_snapshot_pipeline.py`, mocks de provider de
`tests/collectors/test_liga_sweep.py`). `feedback_no_ceremony_specs.md`: um
diretório de fixtures compartilhado adicionaria indireção sem retrabalho
evitado — cada domínio (scripts, collection puro, collectors, services, api,
frontend, cli, integration) já tem exatamente um arquivo de teste dono do seu
builder, e nenhum reaproveita dados de outro além dos helpers de módulo já
citados acima.

## 2. Harnesses por fronteira

### Unit
- **Framework:** pytest (backend, `src/collection/price_history_keys.py` é puro — sem DB) / Vitest + React Testing Library (frontend, `PriceHistoryMeta.tsx`).
- **Comando:** `pytest tests/collection/test_price_history_keys.py tests/services/test_collection_price_history.py tests/collectors/test_price_snapshot_forward_fill.py tests/test_price_snapshot.py tests/api/test_price_history_schemas.py tests/scripts/test_diagnose_collection_history.py -v` e `cd frontend && npx vitest run src/components/__tests__/PriceHistoryMeta.test.tsx`
- **Path padrão:** `tests/collection/*.py`, `tests/services/*.py`, `tests/collectors/*.py`, `frontend/src/components/__tests__/*.test.tsx`

### Integration
- **Framework:** pytest + FastAPI `TestClient` sobre `Repository` real (SQLite in-memory para os endpoints isolados de T08/T09; SQLite em arquivo para T12, pois `run_liga_sweep` abre sua própria engine a partir de `db_url`).
- **Comando:** `pytest tests/api/test_collection_history_resolver.py tests/api/test_cards_history_resolver.py tests/collectors/test_liga_sweep_daily_snapshot.py tests/integration/test_collection_price_history.py tests/integration/test_snapshot_pipeline.py -v`
- **Path padrão:** `tests/api/*.py`, `tests/collectors/test_liga_sweep_daily_snapshot.py`, `tests/integration/test_collection_price_history.py`

### E2E
- **N/A.** O projeto não tem harness de E2E de browser (Playwright/Cypress) configurado
  para fluxos de UI — o Playwright do repo é usado só pelo provider Liga Magic (scraping),
  não para testes de frontend. A cobertura ponta a ponta do bug (AC10/AC11) é feita por
  `tests/integration/test_collection_price_history.py` (pipeline real: sweep fake → snapshot
  → backfill → endpoints, em SQLite) mais o teste de componente `PriceChart.test.tsx`/
  `PriceHistoryMeta.test.tsx` com API mockada — o mesmo padrão já usado em F175. Justificativa
  em 1 linha: montar um harness E2E novo só para esta correção não se paga (`feedback_no_ceremony_specs.md`),
  já coberto por integração real de backend + componente de UI + **AC15 pendente-usuário** (validação
  manual em `homol` com dados reais do Neon, fora do escopo de pytest/vitest).

## 3. Perf budgets

| Métrica | Limite | Como medir | Aplicável a |
|---|---|---|---|
| `load_series` (uma chamada de `build_history`) | 1 única query `SELECT` em `price_observations` (não N+1 por chave/source_card) | Contador via evento SQLAlchemy `before_cursor_execute` filtrando `FROM price_observations` em `test_collection_price_history.py` (T07) | AC "uma única query" / F176-T07 |
| `tests/integration/test_collection_price_history.py` (arquivo inteiro) | < 10 s | Tempo relatado por `pytest tests/integration/test_collection_price_history.py -q` (F176-T12 AC explícita) | F176-T12 |
| Backfill em lote (Neon) | processar em lotes de 500 (sem estourar memória) | Revisão manual do código (paginação por `external_id`), sem asserção de tempo em pytest — não há ambiente Neon em CI | F176-T05 |

Sem budget de latência de rede para os endpoints (`/collection/{id}/history`,
`/metrics`, `/cards/{id}/history`) além da regra "1 query" acima — a feature é
correção de dados/correção de bug, não uma mudança de performance de API, e o
projeto não tem baseline de latência de endpoint documentado para comparar.

## 4. Mocks vs hits real

| Componente | Decisão | Justificativa |
|---|---|---|
| `Repository`/SQLite em `test_price_history_keys.py` (T03) | N/A — módulo puro, sem DB | `resolve_history_keys`/`merge_series_by_priority` não importam `sqlalchemy`/`src.database` (AC explícita); os testes constroem `HistoricalPrice` direto em memória. Mockar aqui não faria sentido — não há dependência a mockar. |
| DB em `test_price_snapshot_forward_fill.py` / `test_price_snapshot.py` (T05) | real (SQLite in-memory) | A lógica em teste é a query de "última observação real por external_id" e o forward-fill em si; mockar o DB esconderia exatamente a regra de carry-forward/backfill que pode quebrar (H6). Custo de SQLite real aqui é baixo. |
| `Repository` em `test_collection_price_history.py` (T07) | real (SQLite in-memory) | AC exige provar "uma única query" e a mesclagem correta por prioridade contra dados reais (foil vs normal, MYP vs Liga); um repo mockado esconderia a query `or_(and_(...))` que é o próprio objeto do teste. |
| Provider Liga em `test_liga_sweep_daily_snapshot.py` (T06) e `test_collection_price_history.py` (T12) | mock (`AsyncMock`, reaproveitando `_mock_provider_search` de `tests/collectors/test_liga_sweep.py`) | Não há rede em testes (regra do projeto); o comportamento em teste é "o sweep chama `run_daily_snapshot` no fim", não o scraping em si — já é o padrão estabelecido nos testes de `liga_sweep` existentes. |
| `run_daily_snapshot` em `test_liga_sweep_daily_snapshot.py`, cenário de falha | mock (patch levantando `RuntimeError`) | Forçar uma falha real do snapshot (ex.: corromper o DB) seria instável; o comportamento em teste é "o sweep não propaga a exceção", então substituir a função por um mock que levanta é a forma mais simples e determinística. |
| `require_auth_or_api_key` / `get_currency_converter_dep` em `test_collection_history_resolver.py` (T08) e `test_collection_price_history.py` (T12) | mock (dependency override do FastAPI, padrão já usado em `tests/api/test_collection_detail.py`) | Autenticação e conversão de moeda são infraestrutura transversal já coberta em outros testes de API; overrides determinísticos evitam configurar OAuth/API externa de câmbio real nesta suíte. |
| `ResponsiveContainer` (Recharts) em `PriceChart.test.tsx` / `PriceHistoryMeta.test.tsx` (T10) | mock | Recharts não renderiza dimensões reais em jsdom; é o padrão já usado nos demais testes de gráfico do repo (`grep -rn "ResponsiveContainer" frontend/src --include=*.test.tsx`). |
| `fetchHistory` no frontend (T10) | mock | Teste de componente, não de rede; segue o padrão de outros testes de `PriceChart`/`Dashboard` do repo — os cenários de `meta` presente/ausente e estados vazios são combinações de resposta que só um mock consegue produzir de forma determinística. |
| `date.today()` / relógio em T05, T06, T07, T12 | mock (parâmetro `today: date | None = None` injetável, já parte do design das tasks) | Testar carry-forward de 30 dias e backfill com `date.today()` real tornaria a suíte dependente da data de execução; todas as tasks já preveem `today` injetável em vez de patch de `datetime`, seguindo o padrão simples pedido nos próprios task files. |
| Neon/Postgres real | real, mas só via script manual (T01: `diagnose_collection_history_neon.sql`) e validação manual (AC15) | O comportamento em produção (contagens de `liga_%`, `liga_%_foil`, pontos/dia) só é confirmável com dados reais; isso é ambiente-dependente e pendente do usuário, não faz parte da suíte automatizada (governance item 3 e 4). |

## 5. Test scenarios resumo

1. Card normal com 3 dias de `liga_{id}` e 0 `source_cards`: script de diagnóstico reporta `current_endpoint_points == 0`, `available_points == 3`, H1 sinalizado — **F176-T01**.
2. Entrada foil (`extras="Foil"`) com `liga_{id}_foil` e `liga_{id}`: diagnóstico reporta ambas séries + `mixed_variants` — **F176-T01**.
3. `daily_snapshot` presente para source_card MYP contado como perdido pelo endpoint atual (H2); mesmo dia liga+myp → `duplicate_dates >= 1` (H5) — **F176-T01**.
4. Edge: `card_id=None` → diagnóstico `unlinked` sem exceção; `--entry-id` inexistente → exit 1; `--sample 0` → resumo vazio sem divisão por zero; contagem de `price_observations` idêntica antes/depois de `main()` (read-only) — **F176-T01**.
5. `resolve_history_keys` normal: inclui `liga/liga_7`, `daily_snapshot/liga_7`, `manual/manual_7`, chaves do source_card MYP + `jsonld_snapshot`/`daily_snapshot`; não inclui `liga_7_foil`. Sem `source_cards` → ainda retorna Liga+manual (regressão H1). `card_id<=0` → `ValueError` — **F176-T03**.
6. `resolve_history_keys` foil: inclui `liga_7_foil` (+snapshot) e `manual_7`; exclui `liga_7` e MYP não-foil; source_card `("myp","123_foil")` incluído; catálogo `liga_catalog_*` só na série normal; duplicados não geram chaves repetidas — **F176-T03**.
7. `merge_series_by_priority`: `liga` vence `myp`/`daily_snapshot` no mesmo dia; dia só com `daily_snapshot` mantido; source desconhecida perde para `myp` e ganha de `daily_snapshot`; empate de prioridade → menor `external_id` vence; `median_price=None` ignorado; saída ASC, ≤1/dia; `SNAPSHOT_SOURCE` igual à constante de `price_snapshot` — **F176-T03**.
8. `PriceHistoryMeta`/`CollectionHistoryResponse.meta`/`PriceObservation.source`: serialização com datas ISO; defaults `meta is None`/`source is None` preservam retrocompatibilidade; `variant="etched"` → `ValidationError`; `aggregate_weekly` continua funcionando sem `source` — **F176-T04**.
9. `run_daily_snapshot`: sem snapshot se última real > 30 dias; exatamente 30 dias → 1 (boundary); um `daily_snapshot` antigo não conta como real; sem snapshot se já há real hoje; 2ª chamada no mesmo dia → 0 — **F176-T05**.
10. `backfill_snapshots`: forward-fill com preço da última real ≤ d, nunca antes da 1ª real; respeita carry-forward de 30 dias mesmo com `days=90`; `dry_run=True` não escreve mas retorna a mesma contagem; idempotente (2ª chamada → 0); `days=0` → `ValueError`; `days=120` → cap 90 + warning — **F176-T05**.
11. `run_liga_sweep(snapshot_after=True)`: sweep com ≥1 processado chama `run_daily_snapshot` 1× e popula `LigaSweepResult.daily_snapshot_created`; `dry_run=True`, `snapshot_after=False` ou 0 elegíveis → não chamado; exceção do snapshot não propaga e não altera contagens; `on_complete` falhar não impede o snapshot — **F176-T06**.
12. `build_history`: card só-Liga sem source_cards → série não vazia (H1); `daily_snapshot` incluído (H2); foil isolado de normal (H4); manual vence no mesmo dia; 1 query por chamada; `days=None` → todo histórico; sem observações → `([], meta)` com `first_observed_at=None`; chave de outro card nunca aparece — **F176-T07**.
13. `/collection/{id}/history` e `/metrics`: card só-Liga com 3 dias sem source_cards → 3 pontos (antes 0); foil → só série `_foil`, `meta.variant="foil"`; `daily_snapshot` aparece com `source="daily_snapshot"`; `card_id=None` → `observations=[]`/`meta=None`; entrada de outro usuário → 404; conversão de moeda mantida; `period` inválido → 422 inalterado — **F176-T08**.
14. `/cards/{id}/history`: card só-Liga retorna pontos (antes vazio); nunca inclui `_foil`; `meta.variant="normal"`; card inexistente → 404; card sem preço → `observations=[]` sem exceção em `compute_price_change_summary` — **F176-T09**.
15. `PriceHistoryMeta.tsx`/`PriceChart.tsx`: badge de variante + fontes traduzidas + "desde" quando `meta` presente; sem `meta` → UI idêntica à atual; estados vazios distintos (`empty-history-never` vs `empty-history-period`); tooltip de `daily_snapshot`; todas as chaves `priceHistory.*` existem em en.json e pt-BR.json; `CollectionCardDetail.tsx` não modificado — **F176-T10**.
16. CLI `backfill-snapshots --dry-run`: aparece no `--help`; não escreve no banco mas reporta a mesma contagem; `daily-snapshot` inalterado; `.bat` chama `python -m src.cli.main daily-snapshot` — **F176-T11**.
17. Integração ponta a ponta: `TestNormalCardHistory` (≥21 pontos D-20..D, 1/dia, sem pontos antes de D-20), `TestFoilCardHistory` (só preços foil), `TestDailyRecording` (sweep grava `daily_snapshot` hoje sem duplicar em 2ª chamada), `TestCrossEndpointConsistency` (`/collection/{id}/history` e `/cards/{id}/history` concordam), `TestRegressionGuards` com um teste nomeado por H1/H2/H4/H5/H6 que falharia no código pré-F176 — **F176-T12**.

## 6. Anotações para tasks

- (F176-T01, `repo`)
- (F176-T03, `card_id_matrix`)
- (F176-T05, `repo`)
- (F176-T06, `_mock_provider_search`)
- (F176-T07, `repo`)
- (F176-T08, `repo`)
- (F176-T09, `repo`)
- (F176-T10, `renderWithMeta`)
- (F176-T11, `repo`)
- (F176-T12, `repo`)

## Riscos para QA

- **AC15 é pendente-usuário, não pytest**: a suíte automatizada (T01–T12) prova a lógica em
  SQLite; a confirmação real de que os cards reportados pelo usuário passam a ter histórico só
  acontece em `homol` com Neon (governance item 3/4). QA não deve marcar PASSED sem essa
  confirmação separada — é bloqueio de promoção para `main`, não veredito de QA.
- **T05 muda a semântica de testes existentes**: `tests/test_price_snapshot.py`,
  `tests/api/test_admin_snapshot.py`, `tests/test_cli_snapshot.py` e
  `tests/integration/test_snapshot_pipeline.py` dependiam do backfill "plano" antigo. QA deve
  conferir que os ajustes nesses arquivos alteram só os asserts que dependiam do comportamento
  antigo (com justificativa no commit), e não removem cobertura de regressão.
- **"Uma única query" (T07) é uma asserção de implementação, não de contrato de API** — se um
  refactor futuro trocar `load_series` sem preservar essa característica, só o teste com o
  evento `before_cursor_execute` pega isso; QA deve confirmar que esse teste específico existe e
  passa antes do merge, já que nenhum outro teste do plano cobriria uma regressão de N+1 queries.
- **F175 exclui foil da série de *market trending*** — se o ADR 0017 concluir que isso deve
  mudar, é um follow-up registrado, não uma correção desta feature; QA deve conferir que
  `test_collection_price_history.py` (T12) não trava o comportamento antigo de F175 em nenhuma
  asserção (governance item 7).
- **Sem harness E2E de browser**: a cobertura de UI é só teste de componente (Vitest/RTL) +
  integração de API real; um bug de integração puramente visual (CSS, layout responsivo) não
  seria pego por nenhum teste deste plano — só pela validação manual do usuário em `homol`
  (mesma limitação apontada para AC15).

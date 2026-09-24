# F176 — Histórico de preços dos cards da coleção (correção definitiva)

**Status:** planned
**PRD:** [`docs/prd/F176-collection-price-history.md`](../../../docs/prd/F176-collection-price-history.md)
**Brief (sharded):** `_brief/00-overview.md`, `01-diagnosis.md`, `02-key-resolution.md`, `03-snapshot-backfill.md`, `04-api-ui.md`
**Lote:** F171–F179 (execução paralela entre features)

## Goal

Fazer o gráfico de histórico de `/collection/:id` mostrar, de forma
confiável, a série de preços **da variante que o usuário possui** (foil ou
normal), com pelo menos um ponto por dia desde a primeira coleta real. O
planejamento já identificou as causas estruturais: o endpoint da coleção só
lê séries de `source_cards` e por isso ignora as chaves `liga_{card_id}`
gravadas pelo Liga sweep; ele também exclui `daily_snapshot` e `manual`,
mistura foil com normal e não deduplica pontos do mesmo dia; e nada grava
`daily_snapshot` automaticamente. A feature começa com um diagnóstico
read-only que confirma essas causas com dados, registra a causa raiz num
ADR, introduz um resolver puro de chaves de histórico, torna a gravação
diária automática e o backfill honesto, corrige os três endpoints de
histórico e a UI, e fecha com um teste de integração ponta a ponta.

## Architecture impact

| Layer | Módulo | Mudança |
|---|---|---|
| Diagnóstico | `scripts/diagnose_collection_history.py` (novo) | Script read-only + relatório |
| Domínio (puro) | `src/collection/price_history_keys.py` (novo) | `resolve_history_keys`, `merge_series_by_priority` |
| Serviço | `src/services/collection_price_history.py` (novo) | `build_history` — 1 query, meta |
| Coleta | `src/collectors/price_snapshot.py` | carry-forward limitado (30d) + backfill forward-fill + dry-run |
| Coleta | `src/collectors/liga_sweep.py` | `snapshot_after=True` → `run_daily_snapshot` no fim do sweep |
| API schemas | `src/api/schemas/collection.py`, `src/api/schemas/cards.py` | `PriceHistoryMeta`, `meta`, `PriceObservation.source` (opcionais) |
| API routers | `src/api/routers/collection.py`, `src/api/routers/cards.py` | history/metrics usam `build_history` |
| Frontend | `PriceChart.tsx`, `PriceHistoryMeta.tsx` (novo), `types/api.ts`, i18n | variante, fontes, "desde", estado vazio |
| CLI / ops | `src/cli/main.py`, `bats/daily-snapshot.bat` (novo) | `backfill-snapshots --dry-run`, rotina diária |
| Docs | ADR 0017, diagramas F176, README | |

**Sem mudanças de schema de banco** (`src/database/models.py` intocado) e sem
edição de `src/database/repository.py`.

## Waves

- **Wave 0**: F176-T01
- **Wave 1**: F176-T02, F176-T03, F176-T04, F176-T05
- **Wave 2**: F176-T06, F176-T07, F176-T10
- **Wave 3**: F176-T08, F176-T09
- **Wave 4**: F176-T11, F176-T12

| Task | Wave | Type | Depends on | Título |
|---|---|---|---|---|
| T01 | 0 | infra/backend | — | Setup + diagnóstico ponta a ponta (script read-only + `diagnosis.md`) |
| T02 | 1 | docs | T01 | ADR de causa raiz + diagramas F176 |
| T03 | 1 | backend | T01 | Resolver puro de chaves + merge por prioridade |
| T04 | 1 | backend | T01 | Schemas: `PriceHistoryMeta`, `meta`, `PriceObservation.source` |
| T05 | 1 | backend | T01 | Snapshot diário com carry-forward limitado + backfill forward-fill |
| T06 | 2 | backend | T05 | Snapshot automático ao fim do liga-sweep |
| T07 | 2 | backend | T03, T04 | Serviço `collection_price_history.build_history` |
| T10 | 2 | frontend | T04 | UI: `PriceHistoryMeta`, estado vazio, tooltip de snapshot, i18n |
| T08 | 3 | backend | T07 | Endpoints history + metrics da coleção usam `build_history` |
| T09 | 3 | backend | T07 | `/cards/{id}/history` usa `build_history` |
| T11 | 4 | infra/docs | T05, T06, T08, T09, T10 | Arquivos compartilhados: `main.py`, `bats/daily-snapshot.bat`, `README.md` |
| T12 | 4 | test | T06, T08, T09 | Teste de integração ponta a ponta (normal + foil) |

## Arquivos tocados por task (detecção de sobreposição entre features)

| Task | Arquivos (N = novo) | Risco no lote |
|---|---|---|
| T01 | `scripts/diagnose_collection_history.py` (N), `tests/scripts/test_diagnose_collection_history.py` (N), `tasks/features/F176-collection-price-history/diagnosis.md` (N) | baixo |
| T02 | `docs/adr/0017-collection-price-history-keys.md` (N — usar o próximo número livre na hora de escrever), `docs/diagrams/F176-architecture.mmd` (N), `docs/diagrams/F176-journey.mmd` (N) | **número de ADR** pode colidir com outra feature do lote → conferir `ls docs/adr` antes de escrever |
| T03 | `src/collection/price_history_keys.py` (N), `tests/collection/test_price_history_keys.py` (N) | baixo |
| T04 | `src/api/schemas/collection.py`, `src/api/schemas/cards.py`, `tests/api/test_price_history_schemas.py` (N) | médio (F171/F174 podem tocar schemas de coleção) — mudança só aditiva |
| T05 | `src/collectors/price_snapshot.py`, `tests/test_price_snapshot.py`, `tests/collectors/test_price_snapshot_forward_fill.py` (N) | baixo |
| T06 | `src/collectors/liga_sweep.py`, `tests/collectors/test_liga_sweep_daily_snapshot.py` (N) | baixo-médio (liga_sweep não citado por outras features do lote) |
| T07 | `src/services/collection_price_history.py` (N), `tests/services/test_collection_price_history.py` (N) | baixo |
| T08 | `src/api/routers/collection.py` (só funções `get_collection_history` e `get_card_metrics`), `tests/api/test_collection_history_resolver.py` (N) | **médio** — F171/F174/F177 podem editar outras partes do router |
| T09 | `src/api/routers/cards.py` (só `get_history`), `tests/api/test_cards_history_resolver.py` (N) | médio |
| T10 | `frontend/src/components/PriceChart.tsx`, `frontend/src/components/PriceHistoryMeta.tsx` (N), `frontend/src/types/api.ts`, `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt-BR.json`, `frontend/src/components/__tests__/PriceHistoryMeta.test.tsx` (N), `frontend/src/components/__tests__/PriceChart.test.tsx` (N — ainda não existe) | **alto** para i18n e `types/api.ts` (compartilhados) — só blocos novos/aditivos |
| T11 | `src/cli/main.py` (só comando `backfill-snapshots`), `bats/daily-snapshot.bat` (N), `README.md`, `tests/test_cli_snapshot.py` | **alto** (arquivos compartilhados do lote) — task pequena, última Wave |
| T12 | `tests/integration/test_collection_price_history.py` (N) | baixo |

**F176 NÃO edita:** `frontend/src/pages/CollectionCardDetail.tsx` (F177 pode
editar), `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx`,
`src/api/app.py`, `src/database/models.py`, `src/database/repository.py`.

## Global acceptance criteria

1. **AC1** — `diagnosis.md` confirma/refuta H1–H6 com números (SQLite local; comandos Neon documentados).
2. **AC2** — ADR registra causa raiz e o contrato de chaves por variante.
3. **AC3** — Para um card de coleção **normal** com observações `liga_{card_id}` em
   ≥3 dias distintos e sem `source_cards`, `GET /api/v1/collection/{id}/history?period=30d`
   retorna ≥3 pontos (hoje retorna 0).
4. **AC4** — Para um card **foil**, a série contém apenas `liga_{card_id}_foil`
   (+ snapshots/manual dessa variante) — nunca preços normais.
5. **AC5** — No máximo 1 ponto por dia; prioridade `manual > liga > jsonld_snapshot > myp > daily_snapshot`.
6. **AC6** — Ao fim de `liga-sweep` (não dry-run, ≥1 processado) existem `daily_snapshot` de hoje.
7. **AC7** — `backfill-snapshots --days 30` nunca cria pontos anteriores à 1ª observação real; idempotente.
8. **AC8** — `daily_snapshot` para de ser gerado 30 dias após a última observação real.
9. **AC9** — `/collection/{id}/metrics` e `/cards/{id}/history` usam a mesma resolução.
10. **AC10** — UI exibe variante, fontes, "histórico desde" e estado vazio explicativo; `CollectionCardDetail.tsx` inalterado.
11. **AC11** — Teste de integração `tests/integration/test_collection_price_history.py` verde.
12. **AC12** — `pytest tests/ --cov=src` e `cd frontend && npm test` verdes; `ruff check src/` limpo; cobertura dos módulos novos ≥ 90%.
13. **AC13** — README atualizado; `bats/daily-snapshot.bat` entregue; diagramas F176 criados.
14. **AC14** — Funciona em SQLite e PostgreSQL (sem SQL específico de dialeto além do já usado no projeto).

## Diagrams

- `docs/diagrams/F176-architecture.mmd` — owner T02
- `docs/diagrams/F176-journey.mmd` — owner T02

## Setup notes (Wave 0)

- Confirmar branch de trabalho: `homol` ou a branch/worktree do lote
  definida pelo orquestrador. **Nunca** `main`.
- Diretórios de teste usados pelas Waves (`tests/scripts/`, `tests/collection/`,
  `tests/services/`, `tests/collectors/`, `tests/integration/`,
  `frontend/src/components/__tests__/`) já existem — T01 só confirma.
- Sem dependências novas (pip/npm).

## Test impact (arquivos de teste existentes afetados)

- `tests/test_price_snapshot.py` — semântica do backfill muda (T05 atualiza).
- `tests/api/test_admin_snapshot.py`, `tests/test_cli_snapshot.py`,
  `tests/integration/test_snapshot_pipeline.py` — devem continuar verdes (assinatura de `run_daily_snapshot` preservada).
- Testes de `get_collection_history` / `get_card_metrics` / `cards.get_history`
  (`grep -rn "/history\|/metrics" tests/api`) — T08/T09 rodam e ajustam fixtures que dependiam do early-return "sem source_cards".
- `tests/collectors/*liga_sweep*` — T06 garante que os mocks aceitam o snapshot pós-sweep (usar `snapshot_after=False` onde o teste não quer o efeito).
- Frontend: testes de `PriceChart` e `CollectionCardDetail*` (`grep -rln PriceChart frontend/src --include=*.test.tsx`).

## Previous attempts (contexto)

F33 (price history), F34 (history metrics), F112 (portfolio history backfill),
F168 (daily snapshot + backfill) — todas corrigiram partes; nenhuma alinhou as
chaves `liga_{card_id}` do sweep com o endpoint da coleção.

## ADR number (batch reservation)
This feature's ADR number is **0017**, reserved in `tasks/features/EXECUTION-PLAN-F171-F179.md`. It overrides any "next free number" instruction in the task files.

## Governance amendments (Saruman G-D-20260924-004: challenge → resolved)

1. **Checkpoint after Wave 0.** The orchestrator reads `diagnosis.md` before Wave 1. It **stops and re-plans the affected tasks** if either of these holds:
   - the root cause differs from the plan's hypothesis (key resolver / merge);
   - the drift since F171/F175/F178 was merged is more than anchor-level.

   Every Wave 1–4 developer must read the "Post-merge drift" section of `diagnosis.md` before editing.
2. **Models.** T01, T03 and T07 run on Opus. The orchestrator sets `developer` to Opus for Waves 0–2 and does not commit that change.
3. **Real-data evidence (pending-user).** T01 also delivers `scripts/diagnose_collection_history_neon.sql`, a read-only query set the user runs against Neon. It returns key-prefix counts and points per day for the cards the user reported. Its output is checked against `diagnosis.md` before the feature is promoted.
4. **Definition of done.** QA PASSED requires one more pending-user step: on `homol`, with real data, the user confirms that the cards and views that failed before now show history. This step is **AC15**.
5. **Backfill marking.** T05 marks forward-filled rows so they can be told apart and deleted. Use a dedicated `source` value such as `daily_snapshot_backfill`, or an equivalent marker documented in ADR 0017. Real snapshots must never look like backfill.
6. **Scheduling.** `push-all.bat` is not in this repo. T06's automatic snapshot at the end of `liga-sweep` is the **primary** mechanism. `bats/daily-snapshot.bat` (T11) is only a manual or backfill fallback, and the README must say so.
7. **F175 interaction.** F175 excludes foil from the *market trending* series. If ADR 0017 concludes that this must change, record it as a follow-up task and adjust T12's assertions. Do not lock the old behaviour in with tests.

**AC15:** the user validates, on `homol` with real (Neon) data, that the originally reported collection cards show price history. This is pending-user and blocks promotion to `main`, not the QA verdict.

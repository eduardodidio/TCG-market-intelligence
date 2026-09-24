# F176 — Overview: histórico de preços dos cards da coleção (correção definitiva)

## Problema

O gráfico de histórico (`PriceChart`) em `/collection/:id`
(`frontend/src/pages/CollectionCardDetail.tsx`) continua vazio ou com 1–2
pontos para a maioria dos cards da coleção, apesar de F33, F34, F112 e F168.
Uma leitura do código durante o planejamento (2026-09-24) já identificou
**causas raiz estruturais** (hipóteses H1–H6 abaixo) que a task de diagnóstico
(T01) deve confirmar com dados reais antes das correções:

| # | Hipótese (evidência no código) | Efeito |
|---|---|---|
| H1 | `GET /api/v1/collection/{id}/history` (`src/api/routers/collection.py` ~L974) só itera `source_cards` do `card_id`. O Liga sweep (`src/collectors/liga_sweep.py` L121/L127), o refresh Liga (`collection.py` L1526) e o scan (`scan.py` L76/82) gravam `source='liga'`, `external_id='liga_{card_id}'` / `'liga_{card_id}_foil'` — **sem linha em `source_cards`**. O catálogo usa `liga_catalog_{set}_{num}` (`src/catalog/seeder.py` L112). | A fonte principal (Liga, preço `mid`) nunca aparece no histórico da coleção. |
| H2 | O endpoint filtra `source IN [sc.source, 'jsonld_snapshot']` — **não inclui `daily_snapshot`** (F168) nem `manual`. O mesmo acontece no `/{entry_id}/metrics` (~L825). (`/cards/{id}/history` em `cards.py` inclui `daily_snapshot`, mas também ignora `liga_{card_id}`.) | Os snapshots diários do F168 nunca chegam ao gráfico da coleção. |
| H3 | Nada agenda `daily-snapshot`: não há `.bat`, o hook pós-scan só grava `portfolio_snapshots`, e o `liga-sweep` do CLI (`src/cli/main.py` ~L1181) registra apenas o alert hook. `get_cards_for_liga_scan(max_age_days=7)` re-varre cada card no máximo 1×/semana. | Na prática ≤1 ponto real por semana por card; sem carry-forward diário. |
| H4 | Foil vs non-foil: o endpoint mistura todas as séries do `card_id` (MYP + qualquer Liga) sem olhar `UserCollectionRow.extras` (`is_foil_entry`). | Para foil, pontos de preços normal e foil intercalados (zig-zag) ou série errada. |
| H5 | Vários pontos no mesmo dia (liga + myp + jsonld_snapshot + daily_snapshot) são concatenados sem dedup (`aggregate_series` só agrega em períodos semanais). | Gráfico serrilhado, `% change` errado. |
| H6 | `backfill_snapshots(days>1)` (`src/collectors/price_snapshot.py`) replica o preço **atual** para os N dias anteriores — dado fabricado — e ignora ids que já têm qualquer `daily_snapshot`. | Histórico plano/falso; backfill não serve como correção. |

## Escopo

1. Diagnóstico ponta a ponta com script read-only + relatório (T01).
2. ADR com a causa raiz e o **contrato de chaves de histórico** + diagramas (T02).
3. Resolver puro de chaves + merge por prioridade/dia (T03); schemas de resposta (T04).
4. Gravação diária confiável (carry-forward limitado T05, snapshot pós-sweep T06, `.bat` T11).
5. Backfill honesto por forward-fill a partir de observações reais (T05).
6. Serviço de histórico da coleção + endpoints history/metrics da coleção e
   `/cards/{id}/history` (T07, T08, T09).
7. UI: variante (foil/normal), fontes, "histórico desde", estado vazio
   explicativo (T10).
8. Teste de integração que garante pontos de histórico para um card de
   coleção (normal e foil) (T12).
9. `bats/daily-snapshot.bat`, flag CLI, README (T11).

## Fora de escopo

- Novas tabelas/migrações (**não tocar `src/database/models.py`**).
- Mudar o formato de `external_id` já gravado ou migrar dados existentes.
- `PriceSparkline`/trends em `CardTile` (usado só em `Cards.tsx`, fora da
  coleção) — registrar no ADR como follow-up se o diagnóstico mostrar o
  mesmo defeito em `get_price_series_batch`.
- Agendador in-process no Render (`src/api/app.py` é arquivo de alto risco).

## Restrições

- Lote F171–F179 paralelo: **não editar** `src/database/models.py`,
  `src/api/app.py`, `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx`.
  Evitar `src/database/repository.py` (5k linhas, alto risco) — queries novas
  vivem no novo serviço `src/services/collection_price_history.py`.
- `src/cli/main.py`, `README.md`, `bats/` só na task final (T11).
- `frontend/src/pages/CollectionCardDetail.tsx` é potencialmente tocado por
  F177 (histórico de banimento dentro do card) — **F176 não edita esse arquivo**;
  a UI nova vive em `PriceChart.tsx` + componente novo.
- i18n (`frontend/src/i18n/locales/{en,pt-BR}.json`) compartilhado — só T10
  edita, com bloco novo `"priceHistory"`.
- Liga usa preço `mid` (CLAUDE.md). Funcionar em SQLite e PostgreSQL (Neon).
- Sem dependências novas.
- Branch: trabalho no `homol` (ou na branch/worktree do lote definida pelo
  orquestrador). Nunca commitar em `main`.

## Critérios de aceite (títulos — detalhe nos shards)

- AC1 Relatório de diagnóstico confirma/refuta H1–H6 com números.
- AC2 ADR `docs/adr/0017-collection-price-history-keys.md` (ou próximo número livre).
- AC3 Resolver de chaves por variante (foil/normal) puro, 100% testado.
- AC4 1 ponto por dia no máximo, escolhido por prioridade de fonte.
- AC5 `daily_snapshot` gravado automaticamente ao fim de cada liga-sweep não-dry-run + `.bat` diário.
- AC6 Backfill forward-fill nunca cria pontos antes da 1ª observação real.
- AC7 History e metrics da coleção retornam pontos Liga/daily_snapshot/manual/MYP da variante correta + `meta`.
- AC8 `/cards/{id}/history` inclui `liga_{card_id}` (variante normal).
- AC9 UI mostra variante, fontes, "desde" e estado vazio explicativo.
- AC10 Teste de integração ponta a ponta verde (normal + foil).
- AC11 README, diagramas F176 e `.bat` entregues.

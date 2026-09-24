# F176 — Diagnóstico: histórico de preços dos cards da coleção

**Task:** F176-T01 (Wave 0) · **Data:** 2026-09-24
**Branch confirmada:** `claude/stoic-mccarthy-nv2690` (branch/worktree do lote; **não é `main`**; base `54411cb` = main após merge F171/F175/F178)

Artefatos:

- `scripts/diagnose_collection_history.py` — diagnóstico read-only por entrada (texto + `--json`)
- `scripts/diagnose_collection_history_neon.sql` — SELECTs read-only para o usuário rodar no Neon
- `tests/scripts/test_diagnose_collection_history.py` — 22 testes (97% de cobertura do script)

## 1. Ambiente

| Item | Valor |
|---|---|
| `tcg_market.db` local | **vazio** (0 linhas em `user_collection`, `source_cards`, `price_observations`, `cards`) |
| `.env` / `DATABASE_URL` | ausente neste ambiente → **sem acesso ao Neon** |
| Base usada | fixture SQLite no scratch (fora do repo, não commitado), montada com os **caminhos de escrita reais** (`repo.insert_price_observations`, `backfill_snapshots`, `run_daily_snapshot`) |
| Validação PostgreSQL | a mesma fixture carregada num PostgreSQL 16 local descartável; `diagnose_collection_history_neon.sql` rodou sem erro e o script Python (`--db postgresql://…`) devolveu os mesmos números |
| Entradas amostradas | 4 (3 linkadas + 1 sem `card_id`), janela 30 dias |

Fixture (reproduz o formato do liga-sweep / F168):

| Entrada | Card | Variante | `source_cards` | Observações reais |
|---|---|---|---|---|
| 1 | Sol Ring (1) | normal | — | `liga/liga_1` em d-1, d-8, d-15, d-22, d-29 (cadência `max_age_days=7`) |
| 2 | Smothering Tithe (2) | **Foil** | — | `liga/liga_2_foil` d-2, 9, 16, 23; `liga/liga_2` d-9, 23 (refresh/scan antigo não-foil) |
| 3 | Rhystic Study (3) | normal | `myp/myp_777` | `myp` d-3, d-17; `jsonld_snapshot` d-3; `liga/liga_3` d-3, 10, 24 |
| 4 | — | normal | — | `card_id = NULL` |

Depois: `backfill_snapshots(days=7)` (35 linhas) + `run_daily_snapshot` (0 — hoje já coberto pelo backfill).

Saída do script (`--days 30`):

```
 entry   card foil  sc avail endpt  lost  dup resolv  flags
     1      1    N   0    12     0    12    1     11  H1,H2,H5,H6
     2      2    Y   0    20     0    20    9     10  H1,H2,H4,H5,H6
     3      3    N   1    20     3    17    7     10  H1,H2,H5,H6
     4   None    N   0     0     0     0    0      0  unlinked

pct_zero_current_endpoint: 75.0   pct_current_ge2_days: 25.0   pct_resolver_ge2_days: 75.0
available_points: 52   current_endpoint_points: 3   lost_points: 49
lost_by_source: {'liga': 14, 'daily_snapshot': 35}   backfilled_snapshots: 30
```

`avail` = observações na janela sob todas as chaves candidatas; `endpt` = o que
`get_collection_history` devolve hoje; `resolv` = dias com ponto usando o
resolver planejado no shard 02 (regra replicada inline no script).

## 2. Hipóteses H1–H6

| # | Hipótese | Status | Número que prova | Evidência de código |
|---|---|---|---|---|
| H1 | Endpoint só lê `source_cards`; Liga (`liga_{id}` / `liga_{id}_foil`) fica de fora | **Confirmada** | 14/14 pontos `liga` perdidos (100%); entradas 1 e 2 → `endpt=0` com 12 e 20 pontos disponíveis; 75% das entradas com 0 pontos no endpoint | `collection.py` L1001–1003 retorna vazio sem `source_cards`; `liga_sweep.py` L121/127, `scan.py` L76/82 e refresh `collection.py` L1526 gravam `liga_{id}[_foil]` sem linha em `source_cards` |
| H2 | Endpoint filtra `[sc.source, 'jsonld_snapshot']`, sem `daily_snapshot`/`manual` | **Confirmada** | 35/35 linhas `daily_snapshot` perdidas; entrada 3 (MYP com `source_card`): 14 `daily_snapshot` perdidos, só 3 pontos devolvidos | `collection.py` L1009 (history) e L826 (metrics); `cards.py` L237 inclui `daily_snapshot` mas só itera `source_cards` |
| H3 | Nada agenda `daily-snapshot`; sweep re-varre ≤1×/semana | **Confirmada (código) / inconclusiva (dados reais)** | Fixture: 4–5 dias reais em 30 (≈1/semana, `real_days_window`); `bats/` só tem `fetch-news.bat` e `process-queue.bat`; o `liga-sweep` do CLI só registra o alert hook | `src/cli/main.py` L1165 (`--max-age-days` default 7), L1181 (só `make_alert_checker_hook`); `daily-snapshot` existe (L2800) mas nada o chama. Freqüência real no Neon: Q3/Q4 do SQL |
| H4 | Foil e normal misturados | **Confirmada** | Entrada 2 (Foil): 11 linhas `liga_2_foil` + 9 `liga_2` para o mesmo card; 9 datas com >1 ponto. O backfill ainda fabricou `daily_snapshot` **para as duas variantes** | Endpoint ignora `extras`/`is_foil_entry`; qualquer merge por `card_id` que inclua `liga_{id}` e `liga_{id}_foil` mistura as variantes |
| H5 | Vários pontos no mesmo dia sem dedup | **Confirmada** | `duplicate_dates` = 1 / 9 / 7 (entradas 1/2/3); até 5 observações no mesmo dia (card 3, d-3: liga + myp + jsonld + 2×daily_snapshot). Já no endpoint atual: `myp`+`jsonld_snapshot` no mesmo dia → `current_endpoint_duplicate_dates=1` | `collection.py` L1015 só ordena e concatena; `aggregate_series` só agrega em períodos semanais |
| H6 | `backfill_snapshots(days>1)` fabrica histórico plano com o preço atual | **Confirmada** | 30/35 linhas `daily_snapshot` têm `observed_at < date(created_at)` (retroativas); 7 dias consecutivos com preço idêntico por série | `price_snapshot.py` `backfill_snapshots`: copia `get_all_latest_prices()` para `today - i`, ignora ids que já têm qualquer `daily_snapshot` |

Critério de detecção do H6 no script/SQL: `run_daily_snapshot` sempre grava
`observed_at = hoje`; uma linha `daily_snapshot` datada antes do dia em que foi
inserida só pode ter vindo de `backfill_snapshots`
(`observed_at < CAST(created_at AS DATE)`).

## 3. Achados novos (não previstos no plano)

1. **`low` vs `mid` na mesma chave `liga_{id}`.** O liga-sweep usa `mid → low → high`
   (`liga_sweep.py`, conforme CLAUDE.md), mas o refresh da coleção
   (`collection.py` L1496/1499) e o scan (`scan.py` L72/79) usam
   `low → mid → high` e gravam **na mesma chave** `source='liga'`,
   `external_id='liga_{id}'`. Com o unique `(source, external_id, observed_at)`,
   quem chega primeiro no dia vence; ao longo dos dias a série alterna entre
   menor anúncio e preço de mercado → serrilhado mesmo depois do merge por dia.
   **Fora do escopo do F176** (não mudar formato/semântica gravada), mas deve ir
   para o ADR (T02) como follow-up.
2. **Backfill contamina a variante errada.** `backfill_snapshots` particiona por
   `external_id`, então um `liga_{id}` antigo e isolado (refresh não-foil de um
   card que o usuário tem em foil) ganha 7–90 dias de `daily_snapshot` fabricados
   — reforça que o resolver foil precisa excluir `liga_{id}` **e** o
   `daily_snapshot` de `liga_{id}`.
3. **Metrics tem o mesmo defeito do history.** `/{entry_id}/metrics`
   (`collection.py` L826) usa a mesma iteração `source_cards × [sc.source,
   'jsonld_snapshot']` — H1/H2/H4/H5 valem para as métricas também (já previsto
   em T08, registrado aqui com a linha atual).
4. **`get_all_latest_prices` ignora a source.** O snapshot diário herda o
   `external_id` da última observação independente da source (`liga`,
   `jsonld_snapshot`, `myp`); como o `external_id` é o mesmo, a série
   `daily_snapshot/myp_777` mistura carry-forward de `myp` e de
   `jsonld_snapshot`. Aceitável (mesmo produto), mas o resolver deve tratá-la
   com a menor prioridade (já previsto: `daily_snapshot = 9`).
5. **Unique constraint entre variantes não colide**, então o resolver pode
   buscar todas as chaves de uma variante numa única query
   `external_id IN (…)` sem risco de linhas cruzadas.

## 4. Post-merge drift (G-D-20260924-004)

Plano escrito antes do merge `2b87481` (F171 + F175 + F178 em `main`). Diff
por arquivo relevante:

| Arquivo | Mudança pós-merge | Impacto no F176 |
|---|---|---|
| `src/api/routers/collection.py` | **F171** (W3/W4): `POST /collection/import` ganhou `currency` (`auto|BRL|USD`), `dry_run` e `rate_lookup`; `batch-add` passa `rate_lookup` e devolve `warnings`; preview inclui `price`/`price_currency`. Linhas deslocaram ~+4 (`get_collection_history` agora L978–1034, metrics L826). | Nenhum. `get_collection_history` e `get_entry_metrics` **inalterados** — H1/H2/H4/H5 continuam válidos. |
| `src/api/schemas/collection.py` | **F171**: `acquisition_price`/`price_currency` em batch-add, campos de moeda em `ImportResult`, `warnings` no `BatchAddResultResponse`. | Nenhum. `CollectionHistoryResponse` inalterado → T04 pode adicionar `meta` opcional como planejado. |
| `src/database/repository.py` | **F175**: `get_trending_price_data` delega para `trending_queries.load_market_trending_prices`. **F178**: novo `get_news_status`. | Nenhum para `get_price_series`/`get_source_cards_for_card`/`SOURCE_PRIORITY` (inalterados; `SOURCE_PRIORITY` ainda sem `daily_snapshot`). |
| `src/database/trending_queries.py` | **F175 (novo)**: `parse_direct_card_id` (regex `^(?:liga|manual)_(\d+)$`) + união `source_cards` ∪ chaves diretas `liga_{id}`/`manual_{id}`, **excluindo** `liga_{id}_foil`. | **Confirma o plano**: F175 já tratou H1 para o trending de mercado com a mesma regra de chave que o resolver normal do shard 02. T03 deve manter a convenção (`liga_{id}` normal, `_foil` separado) e o ADR (T02) deve citar F175 como precedente. `trending_queries` não usa `daily_snapshot` nem dedup por prioridade (usa máximo do dia) — divergência a registrar, não a corrigir aqui. |

**Conclusão:** a hipótese do plano **continua válida**. Nenhum dos merges tocou
o caminho de leitura do histórico da coleção; F175 é evidência adicional de
que a causa é o contrato de chaves (H1).

## 5. Comandos para o Neon (read-only) — pendente usuário

Os números acima são da fixture. Os números de produção dependem do usuário
rodar contra o Neon (`DATABASE_URL` do `.env`). Ambos os comandos só fazem
`SELECT`; o SQL roda dentro de `BEGIN TRANSACTION READ ONLY … ROLLBACK` e o
script marca cada transação PostgreSQL como `READ ONLY` e não cria tabelas.

```bash
# 1) Diagnóstico por entrada (amostra da coleção de um usuário)
python scripts/diagnose_collection_history.py --user-id <seu_user_id> --sample 50 --json f176_neon.json

# 2) Uma entrada específica (o id da URL /collection/:id)
python scripts/diagnose_collection_history.py --entry-id <id> --days 90

# 3) SQL (edite a lista de card ids no CTE `ids` em Q2 e Q5 — marcado "EDIT")
psql "$DATABASE_URL" -f scripts/diagnose_collection_history_neon.sql > f176_neon.txt
```

O que cada query do SQL responde:

| Query | Pergunta | Hipótese |
|---|---|---|
| Q1 | Linhas/séries por família de `external_id` (`liga_%`, `liga_%_foil`, `liga_catalog_%`, `manual_%`, outros) × source | H1, H4 |
| Q2 | Pontos por dia por card (lista de ids), com séries e flags foil/normal | H3, H4, H5 |
| Q3 | Último `daily_snapshot`, dias com snapshot em 30d, linhas retroativas (backfill) | H3, H6 |
| Q4 | Distribuição de dias reais `liga` por série em 90d | H3 |
| Q5 | Endpoint atual vs. disponível por entrada (réplica SQL do script) | H1, H2 |
| Q6 | Cobertura da coleção: sem `card_id`, sem `source_cards`, com Liga direta, foil com `liga_{id}_foil` | H1, H4 |

**Leitura esperada no Neon para fechar AC1:** Q6 `no_source_cards` alto e
`with_direct_liga` ≈ entradas linkadas (H1 em escala); Q3 `last_snapshot_day`
antigo ou `snapshot_days_last_30` ≪ 30 (H3) e `backfilled_rows` > 0 se o
backfill do F168 já rodou (H6). Colar a saída neste arquivo ou no PR.

## 6. Recomendação para o contrato (shard 02)

**Confirma o contrato do shard 02, com dois ajustes a registrar no ADR (T02):**

1. **Manter** o resolver por variante: na fixture ele leva as entradas com ≥2
   dias de 25% → 75% (as linkadas vão de 0/0/3 dias para 11/10/10) e remove
   toda mistura foil/normal. A regra normal é a mesma que o F175 já usa no
   trending (`liga_{id}` + `manual_{id}` + `source_cards`, sem `_foil`).
2. **Manter** `daily_snapshot` como prioridade mais baixa (9) e o merge
   "1 ponto por dia" — com até 5 observações num mesmo dia, o merge por
   prioridade é obrigatório.
3. **Ajuste A (T05/T02):** não usar `daily_snapshot` retroativo como ponto
   "real": `meta.real_points` deve contar só `source != 'daily_snapshot'`
   (já no shard 02). Recomenda-se documentar o critério
   `observed_at < date(created_at)` como forma de identificar backfill antigo
   já gravado no Neon, que **não** será apagado (sem migração de dados — fora
   de escopo).
4. **Ajuste B (follow-up, fora do F176):** unificar `low`/`mid` entre sweep,
   refresh e scan (achado 1). Enquanto isso, o histórico mostra a série como
   gravada.
5. MYP foil: na fixture o MYP não tem chave `_foil`; a regra do shard 02
   (MYP fora da série foil se não tiver `_foil`) se mantém — confirmar com Q1
   no Neon (`other` com `_foil`).

## Nota sobre a fixture de teste (`_fixture_neon_readonly_note`)

`scripts/diagnose_collection_history_neon.sql` não tem fixture pytest: é
validado por execução manual do usuário no Neon. Neste ambiente ele foi
executado uma vez num PostgreSQL 16 local descartável com a fixture acima
(sem erros; Q5 bateu com o script Python: disponível 12/20/20, endpoint 0/0/3).

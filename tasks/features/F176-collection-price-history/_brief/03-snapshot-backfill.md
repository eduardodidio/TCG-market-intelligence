# F176 — Shard 03: Gravação diária + backfill

## Gravação diária (H3)

1. **Pós-sweep** (T06): `run_liga_sweep(..., snapshot_after: bool = True)` em
   `src/collectors/liga_sweep.py`. Ao final de um sweep **não dry-run** com
   `total_processed > 0`, chama `run_daily_snapshot(repo)` dentro de
   `try/except` (log `liga_sweep_daily_snapshot_failed`, nunca propaga) e loga
   `liga_sweep_daily_snapshot` com a contagem. Adicionar
   `daily_snapshot_created: int = 0` ao dataclass `LigaSweepResult`
   (definido em `src/collectors/liga_sweep.py` L24).
   Isso cobre `push-all.bat` → `liga-sweep` (caminho real de produção) sem
   tocar `src/cli/main.py`.
2. **`.bat` dedicado** (T11): `bats/daily-snapshot.bat` chamando
   `python -m src.cli.main daily-snapshot` — rodar 1×/dia (Task Scheduler)
   para dias sem sweep. Seguir o formato de `bats/process-queue.bat`.
3. `run_daily_snapshot` (T05) passa a devolver também quantos ids foram
   considerados (`SnapshotStats` ou dict) — **manter** a função
   `run_daily_snapshot(repo) -> int` com a mesma assinatura (usada por
   `admin.py` L578 e CLI `daily-snapshot`); adicionar
   `run_daily_snapshot_stats(repo) -> dict` se necessário.
4. `run_daily_snapshot` NÃO deve re-snapshotar a partir de um
   `daily_snapshot` indefinidamente sem origem real: o carry-forward vale no
   máximo **`MAX_CARRY_FORWARD_DAYS = 30`** dias após a última observação real
   (source != daily_snapshot). Depois disso o card para de ganhar pontos
   (evita linha plana eterna para cards abandonados). Implementar com query
   própria no módulo (SQLAlchemy Core sobre `PriceObservationRow`) — não
   editar `repository.py`.

## Backfill honesto (H6)

`backfill_snapshots(repo, days=1, dry_run=False) -> int` reescrito como
**forward-fill a partir de observações reais**:

- Para cada `external_id` com observações reais (source != 'daily_snapshot'),
  para cada dia `d` em `[max(today - days + 1, first_real_date), today]`
  sem nenhuma observação desse `external_id` no dia `d`, inserir
  `daily_snapshot` com o preço da **última observação real ≤ d**
  (respeitando `MAX_CARRY_FORWARD_DAYS`).
- **Nunca** cria ponto antes da 1ª observação real.
- Remove o atalho "pula ids que já têm algum daily_snapshot" — idempotência
  vem do unique constraint `(source, external_id, observed_at)` +
  `on_conflict_do_nothing` de `insert_price_observations`.
- `days` continua limitado a `MAX_BACKFILL_DAYS = 90`; `days < 1` → `ValueError`.
- Processar em lotes (500) para não estourar memória no Neon.
- `dry_run=True` → retorna a contagem que seria inserida, sem escrever.
- CLI `backfill-snapshots` ganha `--dry-run` (T11, `main.py`).

## Não fazer

- Não apagar os `daily_snapshot` "planos" já gravados pelo backfill antigo
  (operação destrutiva). Registrar no ADR como limpeza opcional, com
  comando SQL de exemplo, para o usuário decidir.

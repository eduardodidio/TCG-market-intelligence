# F176 — Shard 04: Serviço, endpoints e UI

## Serviço novo: `src/services/collection_price_history.py`

```python
def load_series(repo: Repository, keys: list[SeriesKey], days: int | None) -> list[HistoricalPrice]
    # UMA query: WHERE (source, external_id) IN keys  → usar or_(and_(source==s, external_id==e) ...)
    # ou tuple_().in_() (checar suporte SQLite; or_ é o seguro). observed_at >= today-days quando days.
def first_real_observation(repo, keys) -> date | None
def build_history(repo, card_id: int, is_foil: bool, days: int | None) -> tuple[list[HistoricalPrice], PriceHistoryMetaDict]
    # source_cards = repo.get_source_cards_for_card(card_id)
    # keys = resolve_history_keys(card_id, [(sc.source, sc.external_id) ...], is_foil)
    # merged = merge_series_by_priority(load_series(...))
    # meta = {variant, sources, first_observed_at, last_observed_at, real_points, snapshot_points}
```

Usa `Session(repo.engine)` + `PriceObservationRow` diretamente (mesmo padrão
de `src/collectors/portfolio_backfill.py`) para não editar `repository.py`.

## Endpoints

- `GET /api/v1/collection/{entry_id}/history` (`src/api/routers/collection.py` ~L974):
  substituir o loop de `source_cards` por `build_history(repo, entry.card_id,
  is_foil_entry(entry.extras), days)`; manter conversão de moeda,
  `aggregate_series`, `compute_price_change_summary`; preencher `meta`.
  Remover o early-return "sem source_cards" (cards só-Liga não têm source_cards!).
  `entry.card_id is None` → `observations=[]`, `meta=None` (inalterado).
- `GET /api/v1/collection/{entry_id}/metrics` (~L788): mesma troca de fonte
  de dados (usar `build_history` com `days*2+30`), sem alterar o cálculo.
- `GET /api/v1/cards/{card_id}/history` (`src/api/routers/cards.py` ~L208):
  usar `build_history(repo, card_id, is_foil=False, days)`; remover early
  return "sem source_cards". Resposta ganha `meta` também (mesmo schema).

## UI

- `frontend/src/components/PriceChart.tsx`: aceitar `meta` vindo do
  `fetchHistory` (já retorna `PriceHistoryResponse`), renderizar o componente
  novo `frontend/src/components/PriceHistoryMeta.tsx` acima do gráfico:
  badge variante (Foil ✦ / Normal), fontes ("Liga", "MYP", "Manual",
  "Snapshot diário"), "Histórico desde {data}".
- Estado vazio (`observations.length === 0`) com `meta`:
  - `meta.first_observed_at == null` → "Ainda não há preços registrados para
    esta versão (foil/normal). O histórico começa na próxima varredura Liga."
  - senão → "Sem pontos no período; histórico desde {data}. Tente um período maior."
- Pontos `daily_snapshot`: tooltip indica "preço repetido (sem nova coleta)".
  Para isso, `PriceObservation` ganha campo opcional `source?: string`
  (backend: `PriceObservation` em `src/api/schemas/cards.py` com
  `source: str | None = None` — T04 adiciona; nas agregações semanais pode
  vir `None`). TS: `source?: string | null` em `frontend/src/types/api.ts`.
- **Não editar** `CollectionCardDetail.tsx` (F177). Nada muda na prop
  `fetchHistory`.
- i18n: bloco novo `"priceHistory": {...}` em `en.json` e `pt-BR.json`.

# 02 — Nova query de preços de mercado

## Módulo novo: `src/database/trending_queries.py`
```python
def load_market_trending_prices(engine, period_days: int) -> dict[int, list[tuple[date, Decimal]]]:
```
Retorna o mesmo formato de `Repository.get_trending_price_data`: card_id → [(date, price)],
ordenado por data, um preço por data (em caso de duplicata no mesmo dia, fica o MAIOR — mesma
regra de hoje).

### Fontes (união)
1. **source_cards**: a query atual (JOIN `SourceCardRow` ↔ `PriceObservationRow` em
   `external_id` e `source IN (source_cards.source, 'jsonld_snapshot')`). Copiar como está.
2. **Diretas Liga/manual** (NOVO):
   `PriceObservationRow.source.in_(["liga", "manual"])`, `observed_at >= cutoff`,
   `median_price IS NOT NULL`, `external_id LIKE 'liga\_%' OR LIKE 'manual\_%'`,
   **excluindo** `liga_catalog_%`. Agregar no SQL para reduzir o número de linhas:
   `GROUP BY external_id, observed_at` com `func.max(median_price)`.
   Converter `external_id` → card_id em Python com regex
   `^(?:liga|manual)_(\d+)(?:_foil)?$` (ignorar o que não bater, ex. `liga_catalog_*`).
   Preços manuais são gravados com `source="manual"`, `external_id=f"manual_{card_id}"`
   (`repository.py:439-444`); o Liga sweep usa `source="liga"`. O índice
   `ix_price_obs_card_date (source, external_id, observed_at)` cobre o filtro por source.

### Desempenho
- Postgres: `SET LOCAL statement_timeout = '12s'` (mesmo valor do modo usuário).
- Card não-foil e foil caem no mesmo card_id: dedup por data, fica o maior preço (regra atual).
  Documente a escolha na docstring.
- Opcional, se o T02 mostrar volume alto: filtrar os card_ids com < 3 datas distintas antes de
  voltar (eles seriam descartados por `rank_trending(min_observations=3)`, de qualquer forma).

## Delegação em `repository.py`
Trocar o corpo de `Repository.get_trending_price_data` por:
```python
from src.database.trending_queries import load_market_trending_prices  # import no topo do módulo
...
return load_market_trending_prices(self.engine, period_days)
```
Sem outras edições em `repository.py` (reduz conflito com o lote).
`get_trending_price_data_for_user` NÃO muda.

# F176 — Shard 02: Contrato de chaves de histórico + merge

> **Ajustado pelo ADR 0017** (`docs/adr/0017-collection-price-history-keys.md`): regras de chave
> confirmadas pelo diagnóstico sem mudança. Esclarecimentos: (1) o backfill forward-fill grava
> `source='daily_snapshot_backfill'` (Governance amendment 5), tratado como `daily_snapshot`
> (mesmas chaves por variante, prioridade 9, não conta como ponto real); (2) `meta.real_points`
> exclui todas as sources de snapshot; (3) MYP fica fora da série foil (sem chave `_foil`).

## Módulo novo: `src/collection/price_history_keys.py` (puro, sem DB)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SeriesKey:
    source: str        # 'liga' | 'myp' | 'jsonld_snapshot' | 'daily_snapshot' | 'manual' | outro source_card.source
    external_id: str

SOURCE_PRIORITY: dict[str, int] = {
    "manual": 0, "liga": 1, "jsonld_snapshot": 2, "myp": 3, "daily_snapshot": 9,
}  # manter alinhado a Repository.SOURCE_PRIORITY; daily_snapshot é carry-forward → menor prioridade
UNKNOWN_SOURCE_PRIORITY = 5

def resolve_history_keys(
    card_id: int,
    source_cards: list[tuple[str, str]],   # (source, external_id) de source_cards
    is_foil: bool,
) -> list[SeriesKey]: ...

def merge_series_by_priority(observations: list[HistoricalPrice]) -> list[HistoricalPrice]: ...
```

### Regras de `resolve_history_keys`

Variante **foil** (`is_foil=True`):
1. `('liga', f'liga_{card_id}_foil')`, `('daily_snapshot', f'liga_{card_id}_foil')`
2. `('manual', f'manual_{card_id}')`, `('daily_snapshot', f'manual_{card_id}')`
3. source_cards cujo `external_id` termina com `_foil` (+ `jsonld_snapshot` e
   `daily_snapshot` para cada)
4. **Não** inclui `liga_{card_id}` nem source_cards não-foil. Se T01 mostrar
   que MYP não distingue foil, MYP fica fora da série foil (documentar no ADR).

Variante **normal** (`is_foil=False`):
1. `('liga', f'liga_{card_id}')`, `('daily_snapshot', f'liga_{card_id}')`
2. `('manual', f'manual_{card_id}')`, `('daily_snapshot', f'manual_{card_id}')`
3. Para cada source_card não-foil `(s, e)`: `(s, e)`, `('jsonld_snapshot', e)`,
   `('daily_snapshot', e)` — cobre MYP e `liga_catalog_{set}_{num}`.

Sem duplicatas; ordem determinística (ordem acima). `card_id` inválido (≤0)
→ `ValueError`.

### Regras de `merge_series_by_priority`

- Agrupa por `observed_at` (date); ignora `median_price is None`.
- Por dia escolhe a observação de menor `SOURCE_PRIORITY` (desconhecida = 5);
  empate de prioridade → menor `external_id` em ordem lexicográfica
  (determinístico).
- Retorna ordenado ASC por data, no máximo 1 ponto por dia.

## Contrato de resposta (endpoint da coleção)

`CollectionHistoryResponse` (`src/api/schemas/collection.py`) ganha campo
**opcional** (retrocompatível) — task T04:

```python
class PriceHistoryMeta(BaseModel):
    variant: Literal["foil", "normal"]
    sources: list[str] = []            # sources presentes na série final, ordenadas por prioridade
    first_observed_at: date | None = None   # 1ª observação real (não daily_snapshot) em todo o histórico
    last_observed_at: date | None = None
    real_points: int = 0               # pontos no período cuja source != daily_snapshot
    snapshot_points: int = 0           # pontos daily_snapshot no período

class CollectionHistoryResponse(BaseModel):
    observations: list[PriceObservation] = []
    summary: PriceChangeSummary | None = None
    meta: PriceHistoryMeta | None = None
```

Tipo TS espelhado em `frontend/src/types/api.ts` (T10): `meta?: PriceHistoryMeta | null`.

`PriceObservation` (`src/api/schemas/cards.py` L50) ganha
`source: str | None = None` (T04). Endpoints preenchem com a source vencedora
do dia; `aggregate_weekly` pode devolver `None`.

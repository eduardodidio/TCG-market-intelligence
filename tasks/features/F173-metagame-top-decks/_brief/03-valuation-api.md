# 03 — Valoração BRL e API

## Valoração pura — `src/metagame/valuation.py` (T05)
Sem imports de DB (lição F03/F10: módulos puros).
```python
@dataclass(frozen=True)
class MetaDeckValuation:
    total_value_brl: Decimal | None   # soma price*qty das cartas com preço; None se nenhuma tem preço
    priced_pct: Decimal               # % de cópias (qty) com preço conhecido, 0–100, 1 casa
    owned_pct: Decimal | None         # % de cópias que o usuário possui; None se owned=None (anônimo)
    missing_value_brl: Decimal | None # valor das cópias que faltam (quanto custa completar)
    total_copies: int

def value_meta_deck(cards: Iterable[HasCardIdQty], prices: dict[int, Decimal | None],
                    owned: dict[int, int] | None) -> MetaDeckValuation
```
Regras:
- Considera `board in ("main","commander")` por padrão; `include_sideboard=False` param.
- Cópias possuídas por carta = `min(qty_deck, owned.get(card_id,0))` (não conta 4 cópias
  se o deck pede 1). Cartas com `card_id=None` contam como não possuídas e sem preço.
- **Terrenos básicos** (Plains, Island, Swamp, Mountain, Forest, Wastes, e "Snow-Covered X")
  são tratados como possuídos e com valor 0 (não distorcem % nem valor). Lista em constante.
- Arredondamento `ROUND_HALF_UP` em 2 casas para BRL, 1 casa para %.

Preços: mesmo padrão do ranking em `src/api/routers/decks.py`:
`repo.get_latest_prices_batch(card_ids)` → `obs.median_price` (BRL, fonte Liga `mid`/MYP).

## API — novo router `src/api/routers/meta_decks.py` (T10)
`router = APIRouter(prefix="/meta-decks", tags=["meta-decks"])`, envelope
`ApiResponse`/`success_response` (`src/api/schemas/envelope.py`), auth opcional via
`get_optional_user` (`from src.api.deps import get_db, get_optional_user`).
Schemas no próprio arquivo (padrão `src/api/routers/news.py`) — NÃO editar
`src/api/schemas/*` compartilhados.

| Método | Rota | Query | Resposta |
|---|---|---|---|
| GET | `/api/v1/meta-decks/formats` | – | `{formats: [{format, latest_snapshot_date, deck_count}]}` |
| GET | `/api/v1/meta-decks` | `format` (Literal dos FORMATS, obrigatório), `snapshot_date?`, `limit` 1–50 (20), `offset` ≥0 | `{format, snapshot_date, source, total, decks: [MetaDeckSummary]}` |
| GET | `/api/v1/meta-decks/{deck_id}` | – | `MetaDeckDetail` (summary + `cards: [{name, quantity, board, card_id, price_brl, owned_qty, image_url?}]`) |

`MetaDeckSummary`: `id, rank, archetype, commander_name, colors, meta_share_pct,
deck_count, source, source_url, event_date, snapshot_date, total_value_brl,
priced_pct, owned_pct (null se anônimo), missing_value_brl, total_copies`.

- `format` inválido → 422 (FastAPI Literal). `deck_id` inexistente → 404 via
  `api_error(404, ErrorCode.<existente NOT_FOUND>, ...)` (`src/api/error_codes.py`; usar
  código existente, não adicionar novo — arquivo compartilhado).
- Sem snapshot para o formato → 200 com `decks: []`, `snapshot_date: null`.
- Batch: 1 chamada `get_deck_cards(ids)`, 1 `get_latest_prices_batch(all_ids)`,
  1 `owned_quantities(user_id, all_ids)` por request (Neon: evitar N+1).
- `MetagameRepository` obtido via `MetagameRepository.from_repo(repo)` dentro de uma
  dependency local `get_meta_repo(repo=Depends(get_db))`.
- Testes: montar `FastAPI()` mínimo com `app.include_router(router, prefix="/api/v1")`
  + `dependency_overrides` — o router ainda NÃO está registrado em `src/api/app.py`
  até T15.

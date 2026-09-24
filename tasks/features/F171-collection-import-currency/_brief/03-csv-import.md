# 03 — CSV column mapping, detection, and importer (T04, T07, T10)

## `src/collection/csv_columns.py` (T04, pure)

Canonical fields → accepted headers (compare after `strip().lower()` and accent removal via
`unicodedata.normalize("NFKD")`):

| canonical | Liga (current) | aliases (ManaBox / generic) |
|---|---|---|
| set_code | `Edicao (Sigla)` | `Set code`, `Set`, `Edition code`, `Sigla` |
| collector_number | `Card #` | `Collector number`, `Number`, `Numero` |
| name_en | `Card (EN)` | `Name`, `Card name`, `Card` |
| name_pt | `Card (PT)` | `Nome` |
| set_name_en | `Edicao (EN)` | `Set name` |
| set_name_pt | `Edicao (PTBR)` | — |
| quantity | `Quantidade` | `Quantity`, `Qty`, `Count`, `Qtd` |
| quality | `Qualidade (M NM SP MP HP D)` | `Condition`, `Qualidade` |
| language | `Idioma (BR EN DE ES FR IT JP KO RU TW)` | `Language`, `Idioma` |
| rarity | `Raridade (M R U C)` | `Rarity` |
| color | `Cor (W U B R G M A L)` | — |
| extras | `Extras` | `Foil` (value `foil`/`true` → "Foil") |
| notes | `Comentario` | `Notes`, `Comment` |
| price | — | `Price`, `Purchase price`, `Preço`, `Preco`, `Valor`, `Preço pago`, `Preco (R$)`, `Price (USD)`, `Price (BRL)` — any header starting with price/preco/valor |
| currency | — | `Currency`, `Moeda`, `Purchase price currency` |

```python
@dataclass
class ColumnMap:
    fields: dict[str, str]         # canonical → actual header
    origin: Literal["liga", "manabox", "generic"]
    header_currency: SupportedCurrency | None   # from "(R$)", "(BRL)", "(USD)", "(US$)" in price header

def resolve_columns(headers: list[str]) -> ColumnMap
def detect_file_currency(cmap: ColumnMap, rows: list[dict[str, str]],
                         choice: CurrencyChoice = "auto") -> CurrencyDetection
```

Origin: `liga` if `Edicao (Sigla)` and `Card #` exist. `manabox` if `Purchase price currency` or
(`Set code` and `Collector number`) exist. Otherwise `generic`.

Detection precedence (first match wins; `evidence` lists what was seen):
1. `choice` in {BRL, USD} → source `user`, confidence high.
2. currency column present with ≥1 value in {BRL, USD} → majority value, source `column`
   (per-row values are still honored by the importer; see below).
3. `header_currency` → source `header`.
4. Symbols in the first 200 non-empty price cells (`money.detect_symbol`) → majority, source `symbol`.
   Mixed BRL+USD symbols → majority, confidence low, evidence says "mixed".
5. `number_format_hint` majority over the sample → source `number_format`, confidence low.
6. origin `liga` → BRL, source `origin`, confidence medium.
7. otherwise → BRL, source `default`, confidence low.
Unsupported symbols (€) are collected in `unsupported_symbols`.

## `src/collection/importer.py` (T07)

New signature (backward compatible, keyword-only additions):

```python
def import_collection_csv(engine, csv_path, user_id, *, currency: CurrencyChoice = "auto",
                          rate_lookup: RateLookup | None = None, dry_run: bool = False,
                          today: date | None = None) -> dict
```

- Use `resolve_columns` in place of hardcoded headers. Liga behavior is identical.
- Per row: `raw = row[price_col]`. Row currency: if `choice` is BRL/USD → `choice` (the user wins for
  every row). Otherwise use the row's currency-column value if valid, else the row's own symbol
  (`detect_symbol(raw)`), else `detection.currency`. Then `parse_money(raw, hint=row_currency)` →
  `to_brl(...)` → `acquisition_price`.
- `rate_lookup` None and USD needed → treat as no rate (warning, price None).
- `dry_run=True`: parse and detect only. No `Session`, no delete, returns counts and detection.
- Return dict adds: `detected_currency`, `currency_source`, `currency_confidence`,
  `currency_evidence` (list[str]), `priced` (rows with stored price), `converted` (rows converted USD→BRL),
  `exchange_rate` (str | None), `price_warnings` (list[str], capped to 20 entries + "... and N more").
- `CollectionEntry` / `converter.py`: no change (no monetary fields).
- Quantity parsing must tolerate `"2"`, `""` (→1), `"2.0"`. Invalid → skip row (count as skipped).

## API `POST /api/v1/collection/import` (T10, `src/api/routers/collection.py` ~L1795)

- New query params: `currency: str = Query("auto", pattern="^(auto|BRL|USD)$")`,
  `dry_run: bool = Query(False)`.
- Build `rate_lookup` with `rate_lookup_from_converter(converter)`, where
  `converter: CurrencyConverter = Depends(get_currency_converter_dep)` (already imported in that router).
- `dry_run` → no canonize background task.
- `ImportResult` (`src/api/schemas/collection.py` L61) gains optional fields with defaults:
  `detected_currency: str = "BRL"`, `currency_source: str = "default"`, `currency_confidence: str = "low"`,
  `currency_evidence: list[str] = []`, `priced: int = 0`, `converted: int = 0`,
  `exchange_rate: str | None = None`, `price_warnings: list[str] = []`, `dry_run: bool = False`.

### Frontend contract (T11 consumes it)
`importCollectionCsv(file, { currency = "auto", dryRun = false })` → `POST /api/v1/collection/import?currency=..&dry_run=..`

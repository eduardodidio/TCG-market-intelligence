# 02 — Import-time conversion to BRL (T03)

## `src/currency/import_conversion.py`

```python
RateLookup = Callable[[date], Decimal | None]   # BRL per 1 USD (PTAX), e.g. Decimal("5.40")

@dataclass
class ConversionResult:
    brl: Decimal | None          # None when not convertible
    original_amount: Decimal
    original_currency: str       # "BRL" | "USD" | "EUR" ...
    rate: Decimal | None         # rate applied (None for BRL)
    warning: str | None          # e.g. "no_rate", "unsupported_currency"

def to_brl(amount: Decimal, currency: str, on_date: date, rate_lookup: RateLookup) -> ConversionResult
    # BRL → identity (rate None). USD → amount * rate, quantize 0.01 HALF_UP.
    # USD + rate None → brl None, warning "no_rate". NEVER return the USD amount as BRL.
    # other currencies → brl None, warning "unsupported_currency".

def rate_lookup_from_converter(converter: CurrencyConverter) -> RateLookup
    # returns lambda d: converter.get_display_rate(d)
```

Why the rate is multiplied: `CurrencyConverter.convert` computes `usd = brl / rate`
(`src/services/currency.py`), so `rate` = BRL per USD and `brl = usd * rate`.

`CurrencyConverter(repo)` is built from `Repository` (`src/services/currency.py`).
`get_display_rate(date)` uses `repo.get_closest_rate`, which returns the closest stored PTAX rate.
Do **not** edit `src/services/currency.py`. Wrap it instead.

Rate date: CSV/batch import → `date.today()`. Purchase import → `order_date or date.today()`.

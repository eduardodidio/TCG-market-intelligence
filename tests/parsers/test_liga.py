"""Tests for LigaMagic card page parser."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from src.parsers.liga import (
    LigaPriceData,
    liga_price_to_snapshot,
    parse_card_page,
    parse_price_value,
)

# ---------------------------------------------------------------------------
# Fixtures — realistic HTML snippets mirroring LigaMagic page structure
# ---------------------------------------------------------------------------

LIGHTNING_BOLT_HTML = """
<html>
<head>
<title>Raio / Lightning Bolt - Liga Magic</title>
</head>
<body>
<div class="card-container">
  <h1>Raio / Lightning Bolt</h1>
  <div class="editions-list">
    <div class="edition-row">
      <span class="edition-name">Magic 2010</span>
      <div class="price-section">
        <div class="price-type">Normal</div>
        <div class="priceNormal">
          <span class="price-low">R$ 6,65</span>
          <span class="price-mid">R$ 12,79</span>
          <span class="price-high">R$ 15,00</span>
        </div>
        <div class="price-type">Foil</div>
        <div class="priceFoil">
          <span class="price-low">R$ 18,95</span>
          <span class="price-mid">R$ 25,00</span>
          <span class="price-high">R$ 35,00</span>
        </div>
      </div>
    </div>
  </div>
</div>
</body>
</html>
"""

THOUGHTSEIZE_HTML = """
<html>
<head>
<title>Apreensao de Pensamentos / Thoughtseize - Liga Magic</title>
</head>
<body>
<div class="card-container">
  <h1>Apreensao de Pensamentos / Thoughtseize</h1>
  <div class="editions-list">
    <div class="edition-row">
      <span class="edition-name">Theros</span>
      <div class="price-section">
        <div class="price-type">Normal</div>
        <div class="priceDetails">
          <span class="price-low">R$ 45,56</span>
          <span class="price-mid">R$ 62,86</span>
          <span class="price-high">R$ 120,00</span>
        </div>
        <div class="price-type">Foil</div>
        <div class="priceFoilDetails">
          <span class="price-low">R$ 117,30</span>
          <span class="price-mid">R$ 150,00</span>
          <span class="price-high">R$ 200,00</span>
        </div>
      </div>
    </div>
  </div>
</div>
</body>
</html>
"""

SOL_RING_NORMAL_ONLY_HTML = """
<html>
<head>
<title>Anel de Sol / Sol Ring - Liga Magic</title>
</head>
<body>
<div class="card-container">
  <h1>Anel de Sol / Sol Ring</h1>
  <div class="editions-list">
    <div class="edition-row">
      <span class="edition-name">Commander</span>
      <div class="price-section">
        <div class="price-type">Normal</div>
        <div class="priceNormal">
          <span class="price-low">R$ 9,95</span>
          <span class="price-mid">R$ 14,30</span>
          <span class="price-high">R$ 22,00</span>
        </div>
      </div>
    </div>
  </div>
</div>
</body>
</html>
"""

NO_PRICES_HTML = """
<html>
<head>
<title>Carta Desconhecida / Unknown Card - Liga Magic</title>
</head>
<body>
<div class="card-container">
  <h1>Carta Desconhecida / Unknown Card</h1>
  <div class="editions-list">
    <p>Nenhum resultado encontrado.</p>
  </div>
</div>
</body>
</html>
"""

SINGLE_NAME_HTML = """
<html>
<head>
<title>Black Lotus - Liga Magic</title>
</head>
<body>
<div class="card-container">
  <h1>Black Lotus</h1>
  <div class="price-section">
    <div class="price-type">Normal</div>
    <div class="priceNormal">
      <span class="price-low">R$ 150.000,00</span>
      <span class="price-mid">R$ 200.000,00</span>
      <span class="price-high">R$ 350.000,00</span>
    </div>
  </div>
</div>
</body>
</html>
"""

FOIL_ONLY_HTML = """
<html>
<head>
<title>Carta Foil / Foil Card - Liga Magic</title>
</head>
<body>
<div class="card-container">
  <div class="price-section">
    <div class="price-type">Foil</div>
    <div class="priceFoil">
      <span class="price-low">R$ 50,00</span>
      <span class="price-mid">R$ 75,00</span>
      <span class="price-high">R$ 100,00</span>
    </div>
  </div>
</div>
</body>
</html>
"""

REGEX_FALLBACK_HTML = """
<html>
<head>
<title>Carta Teste / Test Card - Liga Magic</title>
</head>
<body>
<div class="weird-layout">
  <p>Menor preco: R$ 5,00</p>
  <p>Preco medio: R$ 8,50</p>
  <p>Maior preco: R$ 12,00</p>
</div>
</body>
</html>
"""


# ===========================================================================
# Tests: parse_price_value
# ===========================================================================


class TestParsePriceValue:
    """Tests for the parse_price_value function."""

    def test_basic_brazilian_format(self):
        assert parse_price_value("R$ 12,50") == 12.50

    def test_no_space_after_prefix(self):
        assert parse_price_value("R$12,50") == 12.50

    def test_us_format(self):
        assert parse_price_value("R$ 12.50") == 12.50

    def test_thousands_brazilian(self):
        assert parse_price_value("R$ 1.234,56") == 1234.56

    def test_large_number_brazilian(self):
        assert parse_price_value("R$ 150.000,00") == 150000.00

    def test_thousands_us(self):
        assert parse_price_value("R$ 1,234.56") == 1234.56

    def test_integer_price(self):
        assert parse_price_value("R$ 10") == 10.0

    def test_no_prefix(self):
        assert parse_price_value("12,50") == 12.50

    def test_no_prefix_with_dot(self):
        assert parse_price_value("12.50") == 12.50

    def test_zero_price(self):
        assert parse_price_value("R$ 0,00") == 0.0

    def test_empty_string(self):
        assert parse_price_value("") is None

    def test_none_input(self):
        assert parse_price_value(None) is None  # type: ignore[arg-type]

    def test_non_string_input(self):
        assert parse_price_value(123) is None  # type: ignore[arg-type]

    def test_no_digits(self):
        assert parse_price_value("R$ ") is None

    def test_garbage_text(self):
        assert parse_price_value("not a price") is None

    def test_whitespace_only(self):
        assert parse_price_value("   ") is None

    def test_small_price(self):
        assert parse_price_value("R$ 0,10") == 0.10

    def test_price_with_extra_whitespace(self):
        assert parse_price_value("  R$   45,56  ") == 45.56


# ===========================================================================
# Tests: parse_card_page
# ===========================================================================


class TestParseCardPage:
    """Tests for the parse_card_page function."""

    def test_lightning_bolt_names(self):
        result = parse_card_page(LIGHTNING_BOLT_HTML)
        assert result.card_name_pt == "Raio"
        assert result.card_name_en == "Lightning Bolt"

    def test_lightning_bolt_normal_prices(self):
        result = parse_card_page(LIGHTNING_BOLT_HTML)
        assert result.normal_low == 6.65
        assert result.normal_mid == 12.79
        assert result.normal_high == 15.00

    def test_lightning_bolt_foil_prices(self):
        result = parse_card_page(LIGHTNING_BOLT_HTML)
        assert result.foil_low == 18.95
        assert result.foil_mid == 25.00
        assert result.foil_high == 35.00

    def test_thoughtseize_names(self):
        result = parse_card_page(THOUGHTSEIZE_HTML)
        assert result.card_name_pt == "Apreensao de Pensamentos"
        assert result.card_name_en == "Thoughtseize"

    def test_thoughtseize_normal_prices(self):
        result = parse_card_page(THOUGHTSEIZE_HTML)
        assert result.normal_low == 45.56
        assert result.normal_mid == 62.86
        assert result.normal_high == 120.00

    def test_thoughtseize_foil_prices(self):
        result = parse_card_page(THOUGHTSEIZE_HTML)
        assert result.foil_low == 117.30
        assert result.foil_mid == 150.00
        assert result.foil_high == 200.00

    def test_sol_ring_normal_only(self):
        result = parse_card_page(SOL_RING_NORMAL_ONLY_HTML)
        assert result.normal_low == 9.95
        assert result.normal_mid == 14.30
        assert result.normal_high == 22.00
        assert result.foil_low is None
        assert result.foil_mid is None
        assert result.foil_high is None

    def test_no_prices(self):
        result = parse_card_page(NO_PRICES_HTML)
        assert result.card_name_pt == "Carta Desconhecida"
        assert result.card_name_en == "Unknown Card"
        assert result.normal_low is None
        assert result.normal_mid is None
        assert result.normal_high is None
        assert result.foil_low is None
        assert result.foil_mid is None
        assert result.foil_high is None

    def test_single_name_no_slash(self):
        result = parse_card_page(SINGLE_NAME_HTML)
        assert result.card_name_pt == "Black Lotus"
        assert result.card_name_en == "Black Lotus"

    def test_large_prices(self):
        result = parse_card_page(SINGLE_NAME_HTML)
        assert result.normal_low == 150000.00
        assert result.normal_mid == 200000.00
        assert result.normal_high == 350000.00

    def test_foil_only(self):
        result = parse_card_page(FOIL_ONLY_HTML)
        assert result.foil_low == 50.00
        assert result.foil_mid == 75.00
        assert result.foil_high == 100.00

    def test_regex_fallback(self):
        """When no price class/section markers, regex fallback extracts prices."""
        result = parse_card_page(REGEX_FALLBACK_HTML)
        assert result.card_name_pt == "Carta Teste"
        assert result.card_name_en == "Test Card"
        # Regex fallback assigns first 3 prices as normal
        assert result.normal_low == 5.00
        assert result.normal_mid == 8.50
        assert result.normal_high == 12.00

    def test_empty_html(self):
        result = parse_card_page("")
        assert result.card_name_pt is None
        assert result.card_name_en is None
        assert result.normal_low is None

    def test_returns_liga_price_data(self):
        result = parse_card_page(LIGHTNING_BOLT_HTML)
        assert isinstance(result, LigaPriceData)

    def test_no_title_tag(self):
        html = "<html><body><p>No title here</p></body></html>"
        result = parse_card_page(html)
        assert result.card_name_pt is None
        assert result.card_name_en is None


# ===========================================================================
# Tests: liga_price_to_snapshot
# ===========================================================================


class TestLigaPriceToSnapshot:
    """Tests for the liga_price_to_snapshot mapping function."""

    def test_basic_mapping(self):
        price_data = LigaPriceData(
            card_name_pt="Raio",
            card_name_en="Lightning Bolt",
            normal_low=6.65,
            normal_mid=12.79,
            normal_high=15.00,
        )
        ts = datetime(2026, 8, 24, 10, 0, 0)
        snapshot = liga_price_to_snapshot(price_data, "liga_123", observed_at=ts)

        assert snapshot.source == "liga"
        assert snapshot.external_id == "liga_123"
        assert snapshot.observed_at == ts
        assert snapshot.min_price == Decimal("6.65")
        assert snapshot.avg_price == Decimal("12.79")
        assert snapshot.tcg_price is None
        assert snapshot.last_sold_price is None
        assert snapshot.quantity_available is None
        assert snapshot.currency == "BRL"

    def test_mid_as_primary_price(self):
        """normal_mid is the primary price (avg_price)."""
        price_data = LigaPriceData(normal_low=5.0, normal_mid=10.0, normal_high=15.0)
        snapshot = liga_price_to_snapshot(price_data, "test_1")
        assert snapshot.avg_price == Decimal("10.0")

    def test_fallback_to_low_when_no_mid(self):
        """When normal_mid is None, avg_price falls back to normal_low."""
        price_data = LigaPriceData(normal_low=5.0, normal_mid=None)
        snapshot = liga_price_to_snapshot(price_data, "test_2")
        assert snapshot.avg_price == Decimal("5.0")
        assert snapshot.min_price == Decimal("5.0")

    def test_no_prices_at_all(self):
        """When no prices are available, snapshot fields are None."""
        price_data = LigaPriceData()
        snapshot = liga_price_to_snapshot(price_data, "test_3")
        assert snapshot.min_price is None
        assert snapshot.avg_price is None

    def test_default_observed_at(self):
        """Without explicit timestamp, uses current time."""
        price_data = LigaPriceData(normal_mid=10.0)
        before = datetime.now()
        snapshot = liga_price_to_snapshot(price_data, "test_4")
        after = datetime.now()
        assert before <= snapshot.observed_at <= after

    def test_foil_prices_not_in_snapshot(self):
        """Foil prices are stored in LigaPriceData but not mapped to snapshot."""
        price_data = LigaPriceData(
            normal_mid=10.0,
            foil_low=20.0,
            foil_mid=30.0,
            foil_high=40.0,
        )
        snapshot = liga_price_to_snapshot(price_data, "test_5")
        # Snapshot uses normal prices only
        assert snapshot.avg_price == Decimal("10.0")

    def test_snapshot_is_price_snapshot_type(self):
        from src.domain.models import PriceSnapshot

        price_data = LigaPriceData(normal_mid=1.0)
        snapshot = liga_price_to_snapshot(price_data, "x")
        assert isinstance(snapshot, PriceSnapshot)

    def test_decimal_precision(self):
        """Verify float-to-Decimal conversion preserves reasonable precision."""
        price_data = LigaPriceData(normal_low=45.56, normal_mid=62.86)
        snapshot = liga_price_to_snapshot(price_data, "test_6")
        assert snapshot.min_price == Decimal("45.56")
        assert snapshot.avg_price == Decimal("62.86")


# ===========================================================================
# Tests: end-to-end (parse HTML -> snapshot)
# ===========================================================================


class TestEndToEnd:
    """Integration tests: parse HTML then map to PriceSnapshot."""

    def test_lightning_bolt_end_to_end(self):
        price_data = parse_card_page(LIGHTNING_BOLT_HTML)
        ts = datetime(2026, 8, 24, 12, 0, 0)
        snapshot = liga_price_to_snapshot(price_data, "bolt_1", observed_at=ts)

        assert snapshot.source == "liga"
        assert snapshot.min_price == Decimal("6.65")
        assert snapshot.avg_price == Decimal("12.79")
        assert snapshot.currency == "BRL"

    def test_no_prices_end_to_end(self):
        price_data = parse_card_page(NO_PRICES_HTML)
        snapshot = liga_price_to_snapshot(price_data, "unknown_1")

        assert snapshot.source == "liga"
        assert snapshot.min_price is None
        assert snapshot.avg_price is None

    def test_sol_ring_end_to_end(self):
        price_data = parse_card_page(SOL_RING_NORMAL_ONLY_HTML)
        snapshot = liga_price_to_snapshot(price_data, "sol_1")

        assert snapshot.avg_price == Decimal("14.3")
        assert snapshot.min_price == Decimal("9.95")

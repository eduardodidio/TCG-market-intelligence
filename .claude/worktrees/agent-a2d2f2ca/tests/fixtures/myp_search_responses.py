"""Fixture data for MYP search API responses used in integration tests.

Provides realistic but minimal MYP search results, detailed card data,
and price history data for 3-5 cards.  All external_ids, SKUs, and URLs
follow the real MYP format.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from src.domain.models import (
    CardIdentity,
    HistoricalPrice,
    MypSearchResult,
    SourceCard,
)

# ── Search results ──────────────────────────────────────────────


def lightning_bolt_search() -> list[MypSearchResult]:
    """Search results for 'Lightning Bolt' — single exact match on DMR."""
    return [
        MypSearchResult(
            external_id="45231",
            name="Raio / Lightning Bolt",
            slug="raio-lightning-bolt-dmr",
            url="https://mypcards.com/magic/produto/45231/raio-lightning-bolt-dmr",
            sku="magic_dmr_141",
            set_code="dmr",
            collector_number="141",
        ),
    ]


def counterspell_search() -> list[MypSearchResult]:
    """Search results for 'Counterspell' — single exact match on DMR."""
    return [
        MypSearchResult(
            external_id="78442",
            name="Contrafeitico / Counterspell",
            slug="contrafeitico-counterspell-dmr",
            url="https://mypcards.com/magic/produto/78442/contrafeitico-counterspell-dmr",
            sku="magic_dmr_064",
            set_code="dmr",
            collector_number="064",
        ),
    ]


def swords_to_plowshares_search() -> list[MypSearchResult]:
    """Search results for 'Swords to Plowshares' — single exact match on DMR."""
    return [
        MypSearchResult(
            external_id="91205",
            name="Espadas em Arados / Swords to Plowshares",
            slug="espadas-em-arados-swords-to-plowshares-dmr",
            url="https://mypcards.com/magic/produto/91205/espadas-em-arados-swords-to-plowshares-dmr",
            sku="magic_dmr_028",
            set_code="dmr",
            collector_number="028",
        ),
    ]


def dark_ritual_search() -> list[MypSearchResult]:
    """Search results for 'Dark Ritual' — single exact match on DMR."""
    return [
        MypSearchResult(
            external_id="55100",
            name="Ritual Sombrio / Dark Ritual",
            slug="ritual-sombrio-dark-ritual-dmr",
            url="https://mypcards.com/magic/produto/55100/ritual-sombrio-dark-ritual-dmr",
            sku="magic_dmr_067",
            set_code="dmr",
            collector_number="067",
        ),
    ]


def brainstorm_search() -> list[MypSearchResult]:
    """Search results for 'Brainstorm' — single exact match on DMR."""
    return [
        MypSearchResult(
            external_id="62300",
            name="Tempestade Cerebral / Brainstorm",
            slug="tempestade-cerebral-brainstorm-dmr",
            url="https://mypcards.com/magic/produto/62300/tempestade-cerebral-brainstorm-dmr",
            sku="magic_dmr_049",
            set_code="dmr",
            collector_number="049",
        ),
    ]


def empty_search() -> list[MypSearchResult]:
    """Empty search results (no matches found)."""
    return []


# ── Detailed card data (from card page parsing) ────────────────


def lightning_bolt_detail() -> SourceCard:
    return SourceCard(
        source="myp",
        external_id="45231",
        url="https://mypcards.com/magic/produto/45231/raio-lightning-bolt-dmr",
        sku="magic_dmr_141",
        identity=CardIdentity(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="dmr",
            collector_number="141",
        ),
    )


def counterspell_detail() -> SourceCard:
    return SourceCard(
        source="myp",
        external_id="78442",
        url="https://mypcards.com/magic/produto/78442/contrafeitico-counterspell-dmr",
        sku="magic_dmr_064",
        identity=CardIdentity(
            game="magic",
            name_en="Counterspell",
            name_pt="Contrafeitico",
            set_code="dmr",
            collector_number="064",
        ),
    )


def swords_to_plowshares_detail() -> SourceCard:
    return SourceCard(
        source="myp",
        external_id="91205",
        url="https://mypcards.com/magic/produto/91205/espadas-em-arados-swords-to-plowshares-dmr",
        sku="magic_dmr_028",
        identity=CardIdentity(
            game="magic",
            name_en="Swords to Plowshares",
            name_pt="Espadas em Arados",
            set_code="dmr",
            collector_number="028",
        ),
    )


def dark_ritual_detail() -> SourceCard:
    return SourceCard(
        source="myp",
        external_id="55100",
        url="https://mypcards.com/magic/produto/55100/ritual-sombrio-dark-ritual-dmr",
        sku="magic_dmr_067",
        identity=CardIdentity(
            game="magic",
            name_en="Dark Ritual",
            name_pt="Ritual Sombrio",
            set_code="dmr",
            collector_number="067",
        ),
    )


def brainstorm_detail() -> SourceCard:
    return SourceCard(
        source="myp",
        external_id="62300",
        url="https://mypcards.com/magic/produto/62300/tempestade-cerebral-brainstorm-dmr",
        sku="magic_dmr_049",
        identity=CardIdentity(
            game="magic",
            name_en="Brainstorm",
            name_pt="Tempestade Cerebral",
            set_code="dmr",
            collector_number="049",
        ),
    )


# ── Price history ───────────────────────────────────────────────


def make_price_history(
    external_id: str,
    count: int = 5,
    base_price: Decimal = Decimal("10.00"),
    start_date: date | None = None,
) -> list[HistoricalPrice]:
    """Generate a list of HistoricalPrice entries for testing.

    Prices increment by R$0.50 per day from base_price.
    """
    if start_date is None:
        start_date = date(2026, 7, 1)

    return [
        HistoricalPrice(
            source="myp",
            external_id=external_id,
            observed_at=start_date + timedelta(days=i),
            median_price=base_price + Decimal("0.50") * i,
            tcg_price=base_price + Decimal("0.30") * i,
            last_sold_price=base_price + Decimal("0.40") * i,
            quantity_available=10 + i,
            currency="BRL",
        )
        for i in range(count)
    ]


# ── Card fixture metadata (name, set_code, collector_number) ───

CARD_FIXTURES = [
    {
        "name_en": "Lightning Bolt",
        "set_code": "dmr",
        "collector_number": "141",
        "external_id": "45231",
        "search_fn": lightning_bolt_search,
        "detail_fn": lightning_bolt_detail,
    },
    {
        "name_en": "Counterspell",
        "set_code": "dmr",
        "collector_number": "064",
        "external_id": "78442",
        "search_fn": counterspell_search,
        "detail_fn": counterspell_detail,
    },
    {
        "name_en": "Swords to Plowshares",
        "set_code": "dmr",
        "collector_number": "028",
        "external_id": "91205",
        "search_fn": swords_to_plowshares_search,
        "detail_fn": swords_to_plowshares_detail,
    },
    {
        "name_en": "Dark Ritual",
        "set_code": "dmr",
        "collector_number": "067",
        "external_id": "55100",
        "search_fn": dark_ritual_search,
        "detail_fn": dark_ritual_detail,
    },
    {
        "name_en": "Brainstorm",
        "set_code": "dmr",
        "collector_number": "049",
        "external_id": "62300",
        "search_fn": brainstorm_search,
        "detail_fn": brainstorm_detail,
    },
]

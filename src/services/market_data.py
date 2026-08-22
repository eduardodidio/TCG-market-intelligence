"""MarketDataService -- unified facade for all market data access.

Combines Repository (data), CurrencyConverter (currency), and
AggregateCache (performance) into a single entry point.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from src.api.schemas.market_data import (
    CardPriceInfo,
    MarketSummary,
    MoverInfo,
    MoversResult,
)
from src.database.repository import Repository
from src.services.aggregate_cache import (
    TTL_LATEST_PRICES,
    TTL_MARKET_SUMMARY,
    TTL_TOP_MOVERS,
    AggregateCache,
)
from src.services.currency import CurrencyConverter

PERIOD_MAP = {
    "24h": 1,
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "180d": 180,
    "1y": 365,
    "3y": 1095,
}


class MarketDataService:
    """Unified facade for all market data access.

    Combines Repository (data), CurrencyConverter (currency), and
    AggregateCache (performance) into a single entry point.
    """

    def __init__(
        self,
        repo: Repository,
        converter: CurrencyConverter,
        cache: AggregateCache | None = None,
    ) -> None:
        self._repo = repo
        self._converter = converter
        self._cache = cache or AggregateCache()

    # ------------------------------------------------------------------
    # Price lookups
    # ------------------------------------------------------------------

    def get_latest_price(
        self,
        card_id: int,
        currency: str = "BRL",
    ) -> CardPriceInfo | None:
        """Get latest price for a single card, currency-converted."""
        cache_key = f"latest_price:{card_id}"
        cached = self._cache.get(cache_key)

        if cached is None:
            batch = self._repo.get_latest_prices_batch([card_id])
            obs = batch.get(card_id)
            if obs is None:
                return None
            # Cache the raw BRL data
            cached = {
                "card_id": card_id,
                "price": obs.median_price,
                "date": obs.observed_at,
            }
            self._cache.set(
                cache_key,
                cached,
                ttl=TTL_LATEST_PRICES,
                tags={f"card:{card_id}"},
            )

        # Apply currency conversion
        today = date.today()
        converted_price = self._convert_price(cached["price"], today, currency)
        actual_currency = currency if converted_price is not None else "BRL"
        if converted_price is None:
            converted_price = Decimal(str(cached["price"])) if cached["price"] is not None else None

        return CardPriceInfo(
            card_id=cached["card_id"],
            latest_price=converted_price,
            price_date=cached["date"],
            currency=actual_currency,
        )

    def get_cards_with_prices(
        self,
        card_ids: list[int],
        currency: str = "BRL",
    ) -> dict[int, CardPriceInfo]:
        """Batch price lookup with caching and currency conversion."""
        result: dict[int, CardPriceInfo] = {}
        miss_ids: list[int] = []

        # Check cache for each card
        for cid in card_ids:
            cache_key = f"latest_price:{cid}"
            cached = self._cache.get(cache_key)
            if cached is not None:
                result[cid] = self._build_price_info(cached, currency)
            else:
                miss_ids.append(cid)

        # Fetch misses from repo
        if miss_ids:
            batch = self._repo.get_latest_prices_batch(miss_ids)
            for cid in miss_ids:
                obs = batch.get(cid)
                if obs is None:
                    continue
                raw = {
                    "card_id": cid,
                    "price": obs.median_price,
                    "date": obs.observed_at,
                }
                self._cache.set(
                    f"latest_price:{cid}",
                    raw,
                    ttl=TTL_LATEST_PRICES,
                    tags={f"card:{cid}"},
                )
                result[cid] = self._build_price_info(raw, currency)

        return result

    # ------------------------------------------------------------------
    # Movers
    # ------------------------------------------------------------------

    def get_top_movers(
        self,
        period: str = "30d",
        limit: int = 10,
        currency: str = "BRL",
    ) -> MoversResult:
        """Get top price gainers and losers, cached."""
        cache_key = f"movers:{period}:{limit}"
        cached = self._cache.get(cache_key)

        if cached is None:
            days = PERIOD_MAP.get(period, 30)
            gainers_raw, losers_raw = self._repo.get_movers(days=days, limit=limit)
            cached = {
                "gainers": gainers_raw,
                "losers": losers_raw,
                "computed_at": datetime.now(),
            }
            self._cache.set(
                cache_key,
                cached,
                ttl=TTL_TOP_MOVERS,
                tags={f"movers:{period}"},
            )

        today = date.today()
        actual_currency = self._resolve_currency(currency)

        gainers = [self._build_mover_info(g, today, actual_currency) for g in cached["gainers"]]
        losers = [self._build_mover_info(lo, today, actual_currency) for lo in cached["losers"]]

        return MoversResult(
            gainers=gainers,
            losers=losers,
            period=period,
            currency=actual_currency,
            computed_at=cached["computed_at"],
        )

    # ------------------------------------------------------------------
    # Market summary
    # ------------------------------------------------------------------

    def get_market_summary(
        self,
        currency: str = "BRL",
        game: str | None = None,
    ) -> MarketSummary:
        """Get aggregate market statistics, cached."""
        cache_key = f"market_summary:{game or 'all'}"
        cached = self._cache.get(cache_key)

        if cached is None:
            stats = self._repo.get_market_stats(game=game)
            cached = {
                "stats": stats,
                "computed_at": datetime.now(),
            }
            self._cache.set(
                cache_key,
                cached,
                ttl=TTL_MARKET_SUMMARY,
                tags={"market_summary"},
            )

        stats = cached["stats"]
        actual_currency = self._resolve_currency(currency)

        avg = stats["avg_price"]
        if avg is not None:
            avg = Decimal(str(round(float(avg), 2)))
            converted = self._convert_price(avg, date.today(), actual_currency)
            if converted is not None:
                avg = converted
            elif actual_currency != "BRL":
                # Conversion failed, fall back to BRL
                actual_currency = "BRL"

        return MarketSummary(
            total_cards=stats["total_cards"],
            total_observations=stats["total_observations"],
            avg_price=avg,
            date_range_start=stats["date_range_start"],
            date_range_end=stats["date_range_end"],
            currency=actual_currency,
            computed_at=cached["computed_at"],
        )

    # ------------------------------------------------------------------
    # Cache invalidation
    # ------------------------------------------------------------------

    def invalidate_cards(self, card_ids: list[int]) -> None:
        """Clear cached data for specific cards plus global caches."""
        tags: set[str] = {f"card:{cid}" for cid in card_ids}
        tags.add("market_summary")
        # Invalidate all mover period caches
        for period_key in PERIOD_MAP:
            tags.add(f"movers:{period_key}")
        self._cache.invalidate_by_tags(tags)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_currency(self, currency: str) -> str:
        """Resolve actual currency, falling back to BRL if no rate."""
        if currency not in ("BRL", "PILA"):
            rate = self._converter.get_display_rate()
            if rate is None:
                return "BRL"
        return currency

    def _convert_price(
        self,
        value: Decimal | float | None,
        from_date: date,
        currency: str,
    ) -> Decimal | None:
        """Convert price via the CurrencyConverter."""
        return self._converter.convert(value, from_date, currency)

    def _build_price_info(
        self,
        raw: dict,
        currency: str,
    ) -> CardPriceInfo:
        """Build a CardPriceInfo from cached raw data with conversion."""
        today = date.today()
        converted = self._convert_price(raw["price"], today, currency)
        actual_currency = currency if converted is not None else "BRL"
        if converted is None:
            converted = Decimal(str(raw["price"])) if raw["price"] is not None else None
        return CardPriceInfo(
            card_id=raw["card_id"],
            latest_price=converted,
            price_date=raw["date"],
            currency=actual_currency,
        )

    def _build_mover_info(
        self,
        raw_tuple: tuple,
        from_date: date,
        currency: str,
    ) -> MoverInfo:
        """Build a MoverInfo from a repo raw tuple with conversion."""
        card_id, name_en, name_pt, set_code, price_start, price_end, change_pct = raw_tuple
        return MoverInfo(
            card_id=card_id,
            name_en=name_en,
            name_pt=name_pt,
            set_code=set_code,
            price_start=self._convert_price(price_start, from_date, currency),
            price_end=self._convert_price(price_end, from_date, currency),
            change_pct=change_pct,
            currency=currency,
        )

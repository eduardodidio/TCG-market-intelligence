"""Trending cards service with in-memory caching (F36)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from src.analytics.trending import compute_trending_score, rank_trending
from src.api.schemas.trending import TrendingCardEntry, TrendingResponse
from src.database.repository import Repository
from src.services.currency import CurrencyConverter
from src.utils.set_code_map import map_to_scryfall_set_code


def _scryfall_image_url(set_code: str | None, collector_number: str | None) -> str | None:
    if not set_code or not collector_number:
        return None
    mapped = map_to_scryfall_set_code(set_code)
    return (
        f"https://api.scryfall.com/cards/{mapped}/{collector_number}"
        f"?format=image&version=normal"
    )


class TrendingService:
    """Compute and cache trending card rankings."""

    def __init__(self, repo: Repository):
        self._repo = repo
        self._cache: dict[str, tuple[datetime, TrendingResponse]] = {}
        self._cache_ttl = timedelta(minutes=30)

    def get_trending(
        self,
        direction: str,
        period_days: int,
        limit: int,
        converter: CurrencyConverter,
        currency: str,
        user_id: int | None = None,
    ) -> TrendingResponse:
        """Return cached or freshly computed trending cards."""
        scope = f"user_{user_id}" if user_id is not None else "all"
        cache_key = f"{direction}:{period_days}:{scope}"
        now = datetime.now()

        cached_entry = self._cache.get(cache_key)
        if cached_entry is not None:
            cached_at, cached_response = cached_entry
            if now - cached_at < self._cache_ttl:
                # Return cached data with fresh currency conversion
                return self._apply_currency(
                    cached_response, converter, currency, limit, cached=True
                )

        # Cache miss: compute fresh data
        if user_id is not None:
            price_data = self._repo.get_trending_price_data_for_user(user_id, period_days)
        else:
            price_data = self._repo.get_trending_price_data(period_days)

        scores = []
        for card_id, card_prices in price_data.items():
            score = compute_trending_score(card_id, card_prices, period_days)
            if score is not None:
                scores.append(score)

        ranked = rank_trending(scores, direction, limit=limit)

        # Load card metadata
        card_ids = [s.card_id for s in ranked]
        card_info = self._repo.get_card_info_batch(card_ids)

        # Build entries (BRL-denominated for caching)
        entries = []
        for s in ranked:
            info = card_info.get(s.card_id, ("Unknown", None, None, None))
            name_en, name_pt, set_code, collector_number = info
            entries.append(
                TrendingCardEntry(
                    card_id=s.card_id,
                    name_en=name_en,
                    name_pt=name_pt,
                    set_code=set_code,
                    collector_number=collector_number,
                    image_url=_scryfall_image_url(set_code, collector_number),
                    price_start=float(s.price_start),
                    price_end=float(s.price_end),
                    change_pct=float(s.change_pct),
                    change_abs=float(s.change_abs),
                    consistency=float(s.consistency),
                    composite_score=float(s.composite_score),
                    observation_count=s.observation_count,
                    currency="BRL",
                )
            )

        response = TrendingResponse(
            cards=entries,
            period=f"{period_days}d",
            direction=direction,
            computed_at=now,
            cached=False,
        )

        # Cache the BRL-denominated result
        self._cache[cache_key] = (now, response)

        return self._apply_currency(response, converter, currency, limit, cached=False)

    def invalidate_cache(self) -> None:
        """Clear all cached trending data."""
        self._cache.clear()

    def _apply_currency(
        self,
        response: TrendingResponse,
        converter: CurrencyConverter,
        currency: str,
        limit: int,
        cached: bool,
    ) -> TrendingResponse:
        """Apply currency conversion and limit to a response."""
        today = date.today()

        # Check if conversion is possible for non-BRL currencies
        actual_currency = currency
        if currency not in ("BRL", "PILA"):
            rate = converter.get_display_rate()
            if rate is None:
                actual_currency = "BRL"

        converted_cards = []
        for card in response.cards[:limit]:
            if actual_currency != "BRL":
                from decimal import Decimal

                price_start = converter.convert(
                    Decimal(str(card.price_start)), today, actual_currency
                )
                price_end = converter.convert(Decimal(str(card.price_end)), today, actual_currency)
                change_abs = converter.convert(
                    Decimal(str(card.change_abs)), today, actual_currency
                )
                converted_cards.append(
                    TrendingCardEntry(
                        card_id=card.card_id,
                        name_en=card.name_en,
                        name_pt=card.name_pt,
                        set_code=card.set_code,
                        collector_number=card.collector_number,
                        image_url=card.image_url,
                        price_start=float(price_start)
                        if price_start is not None
                        else card.price_start,
                        price_end=float(price_end) if price_end is not None else card.price_end,
                        change_pct=card.change_pct,
                        change_abs=float(change_abs) if change_abs is not None else card.change_abs,
                        consistency=card.consistency,
                        composite_score=card.composite_score,
                        observation_count=card.observation_count,
                        currency=actual_currency,
                    )
                )
            else:
                converted_cards.append(card.model_copy(update={"currency": actual_currency}))

        return TrendingResponse(
            cards=converted_cards,
            period=response.period,
            direction=response.direction,
            computed_at=response.computed_at,
            cached=cached,
        )

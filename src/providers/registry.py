"""Provider registry with ordered fallback chain."""

from __future__ import annotations

import structlog

from src.domain.interfaces import CardSourceProvider
from src.domain.models import HistoricalPrice, PriceSnapshot, SourceCard

log = structlog.get_logger()


class ProviderRegistry:
    """Tries providers in priority order, falling back on failure."""

    def __init__(self, providers: list[CardSourceProvider]) -> None:
        self.providers = providers

    @property
    def source_names(self) -> list[str]:
        """Return list of source names in priority order."""
        return [p.source_name for p in self.providers]

    async def get_current_price(self, card: SourceCard) -> PriceSnapshot | None:
        """Try each provider in order until one returns a price."""
        for provider in self.providers:
            try:
                price = await provider.get_current_price(card)
                if price is not None:
                    log.info(
                        "price_found",
                        source=provider.source_name,
                        card=card.external_id,
                    )
                    return price
                log.debug(
                    "no_price",
                    source=provider.source_name,
                    card=card.external_id,
                )
            except Exception as exc:
                log.warning(
                    "provider_error",
                    source=provider.source_name,
                    card=card.external_id,
                    error=str(exc),
                )
                continue
        return None

    async def get_price_history(self, card: SourceCard, days: int = 1095) -> list[HistoricalPrice]:
        """Try each provider in order until one returns history."""
        for provider in self.providers:
            try:
                history = await provider.get_price_history(card, days)
                if history:
                    return history
            except Exception:
                continue
        return []

    async def discover_sets(self) -> list[str]:
        """Aggregate sets from all providers."""
        all_sets: set[str] = set()
        for provider in self.providers:
            try:
                sets = await provider.discover_sets()
                all_sets.update(sets)
            except Exception:
                continue
        return sorted(all_sets)

    async def discover_cards(self, set_id: str | None = None) -> list[SourceCard]:
        """Use first provider that returns cards."""
        for provider in self.providers:
            try:
                cards = await provider.discover_cards(set_id)
                if cards:
                    return cards
            except Exception:
                continue
        return []


def create_registry_from_env() -> ProviderRegistry:
    """Create registry with MYP as the sole provider."""
    from src.providers.myp.provider import MypCardsProvider

    providers: list[CardSourceProvider] = [MypCardsProvider()]
    return ProviderRegistry(providers)

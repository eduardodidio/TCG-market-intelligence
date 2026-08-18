from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import CardIdentity, HistoricalPrice, PriceSnapshot, SourceCard


class CardSourceProvider(ABC):
    """Abstract interface for a card data source."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        ...

    @abstractmethod
    async def discover_sets(self) -> list[str]:
        """Return list of set identifiers available at this source."""
        ...

    @abstractmethod
    async def discover_cards(self, set_id: str | None = None) -> list[SourceCard]:
        """Discover cards, optionally filtered by set."""
        ...

    @abstractmethod
    async def get_current_price(self, card: SourceCard) -> PriceSnapshot | None:
        """Get current price data for a card."""
        ...

    @abstractmethod
    async def get_price_history(
        self, card: SourceCard, days: int = 1095
    ) -> list[HistoricalPrice]:
        """Get historical price data for a card."""
        ...

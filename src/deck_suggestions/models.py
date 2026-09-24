"""ORM row for the deck-suggestion request queue (F172).

Lives in its own module (not ``src/database/models.py``) but shares the
declarative ``Base``. The table is created idempotently by
``src.deck_suggestions.repository.ensure_table``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.models import Base


class DeckSuggestionRequestRow(Base):
    """Persistent queue of deck-suggestion requests.

    Users submit requests via the API; a local daily routine claims pending
    rows, asks Claude to build the deck and stores the result as JSON text.
    """

    __tablename__ = "deck_suggestion_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    format_name: Mapped[str] = mapped_column(String(30), nullable=False)
    commander_card_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cards.id", ondelete="SET NULL")
    )
    # Denormalized so it survives card deletion
    commander_name: Mapped[str | None] = mapped_column(String(500))
    # WUBRG-ordered letters ("WUB"); "C" = colorless
    colors: Mapped[str | None] = mapped_column(String(10))
    archetype: Mapped[str | None] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # status values: pending, processing, done, failed
    result_json: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    saved_deck_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("decks.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("ix_deck_sugg_req_user", "user_id"),
        Index("ix_deck_sugg_req_status", "status"),
        Index("ix_deck_sugg_req_created", "created_at"),
    )

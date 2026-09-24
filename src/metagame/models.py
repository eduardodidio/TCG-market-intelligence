"""SQLAlchemy models for metagame (market top decks) snapshots.

Kept outside ``src/database/models.py`` on purpose (high-conflict file); the
tables share the same declarative ``Base`` and are created on demand by
``MetagameRepository``.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.database.models import Base


class MetaDeckRow(Base):
    __tablename__ = "meta_decks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    archetype: Mapped[str] = mapped_column(String(200), nullable=False)
    commander_name: Mapped[str | None] = mapped_column(String(300))
    colors: Mapped[str | None] = mapped_column(String(10))
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_share_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    deck_count: Mapped[int | None] = mapped_column(Integer)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    event_date: Mapped[date | None] = mapped_column(Date)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint(
            "source", "format", "external_id", "snapshot_date", name="uq_meta_deck_snapshot"
        ),
        Index("ix_meta_decks_fmt_snap_rank", "format", "snapshot_date", "rank"),
    )


class MetaDeckCardRow(Base):
    __tablename__ = "meta_deck_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meta_deck_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meta_decks.id", ondelete="CASCADE"), nullable=False
    )
    card_name: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    board: Mapped[str] = mapped_column(String(10), nullable=False, default="main")
    card_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cards.id", ondelete="SET NULL")
    )

    __table_args__ = (
        Index("ix_meta_deck_cards_deck", "meta_deck_id"),
        Index("ix_meta_deck_cards_card", "card_id"),
    )

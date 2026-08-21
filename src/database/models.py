from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CardRow(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    game: Mapped[str] = mapped_column(String(50), nullable=False)
    name_en: Mapped[str] = mapped_column(String(500), nullable=False)
    name_pt: Mapped[str | None] = mapped_column(String(500))
    set_code: Mapped[str | None] = mapped_column(String(20))
    collector_number: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        UniqueConstraint("game", "set_code", "collector_number", name="uq_card_identity"),
        Index("ix_card_game_set", "game", "set_code"),
        Index("ix_card_name_en", "name_en"),
    )


class SourceCardRow(Base):
    __tablename__ = "source_cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    card_id: Mapped[int | None] = mapped_column(Integer)
    sku: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(500))
    name_pt: Mapped[str | None] = mapped_column(String(500))
    set_code: Mapped[str | None] = mapped_column(String(20))
    collector_number: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_source_card"),
        Index("ix_source_card_sku", "sku"),
    )


class PriceObservationRow(Base):
    __tablename__ = "price_observations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    observed_at: Mapped[date] = mapped_column(Date, nullable=False)
    median_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    tcg_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    last_sold_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    quantity_available: Mapped[int | None] = mapped_column(Integer)
    last_sold_meta: Mapped[str | None] = mapped_column(String(200))
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("source", "external_id", "observed_at", name="uq_price_observation"),
        Index("ix_price_obs_card_date", "source", "external_id", "observed_at"),
    )


class UserCollectionRow(Base):
    __tablename__ = "user_collection"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    card_id: Mapped[int | None] = mapped_column(Integer)
    set_code: Mapped[str] = mapped_column(String(20), nullable=False)
    collector_number: Mapped[str] = mapped_column(String(20), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(500))
    name_pt: Mapped[str | None] = mapped_column(String(500))
    set_name_en: Mapped[str | None] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    quality: Mapped[str | None] = mapped_column(String(10))
    language: Mapped[str | None] = mapped_column(String(10))
    rarity: Mapped[str | None] = mapped_column(String(5))
    color: Mapped[str | None] = mapped_column(String(10))
    extras: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("ix_user_collection_user", "user_id"),
        Index("ix_user_collection_card", "card_id"),
    )


class CollectionErrorRow(Base):
    __tablename__ = "collection_errors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    resolved: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (Index("ix_error_unresolved", "resolved", "source"),)


class ScanRunRow(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    filters_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    cards_total: Mapped[int] = mapped_column(Integer, default=0)
    cards_processed: Mapped[int] = mapped_column(Integer, default=0)
    cards_failed: Mapped[int] = mapped_column(Integer, default=0)
    observations_saved: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("ix_scan_runs_status", "status"),
        Index("ix_scan_runs_type_date", "scan_type", "created_at"),
    )

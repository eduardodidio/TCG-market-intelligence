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
    set_name_pt: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(String(500))
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


class ScheduledScanRow(Base):
    __tablename__ = "scheduled_scans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    scan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    filters_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    last_run_id: Mapped[int | None] = mapped_column(Integer)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("ix_scheduled_scans_status", "status"),
        Index("ix_scheduled_scans_user", "user_id"),
    )


class ExchangeRateRow(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    from_currency: Mapped[str] = mapped_column(String(3), default="USD")
    to_currency: Mapped[str] = mapped_column(String(3), default="BRL")
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="bcb_ptax")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (Index("ix_exchange_rate_date", "rate_date"),)


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    avatar_url: Mapped[str | None] = mapped_column(String(1000))
    auth_provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_id: Mapped[str | None] = mapped_column(String(200))
    password_hash: Mapped[str | None] = mapped_column(String(200))
    password_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    preferred_currency: Mapped[str] = mapped_column(String(10), default="BRL")
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    is_admin: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_provider", "auth_provider"),
        UniqueConstraint("auth_provider", "provider_id", name="uq_user_provider"),
    )


class DeckRow(Base):
    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (Index("ix_decks_user", "user_id"),)


class CardLegalityRow(Base):
    __tablename__ = "card_legalities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_date: Mapped[date | None] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        UniqueConstraint("card_id", "format", name="uq_card_legality"),
        Index("ix_legality_format_status", "format", "status"),
    )


class LegalityHistoryRow(Base):
    __tablename__ = "legality_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String(50), nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(20))
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="scryfall_sync")

    __table_args__ = (Index("ix_legality_history_card_format", "card_id", "format", "changed_at"),)


class DeckCardRow(Base):
    __tablename__ = "deck_cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    deck_id: Mapped[int] = mapped_column(Integer, nullable=False)
    set_code: Mapped[str | None] = mapped_column(String(20))
    collector_number: Mapped[str | None] = mapped_column(String(20))
    name_en: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    card_id: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        Index("ix_deck_cards_deck", "deck_id"),
        Index("ix_deck_cards_card", "card_id"),
    )


class CreditBalanceRow(Base):
    __tablename__ = "credit_balances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_bonus_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_monthly_grant_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (Index("ix_credit_balance_user", "user_id"),)


class CreditTransactionRow(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("ix_credit_tx_user", "user_id"),
        Index("ix_credit_tx_user_date", "user_id", "created_at"),
    )


class SharedCollectionRow(Base):
    __tablename__ = "shared_collections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    is_shared: Mapped[int] = mapped_column(Integer, default=0)  # 0=private, 1=shared
    share_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    shared_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("ix_shared_collection_user", "user_id"),
        Index("ix_shared_collection_code", "share_code"),
    )


class TradeInterestRow(Base):
    __tablename__ = "trade_interests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    buyer_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    seller_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    collection_entry_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # status: pending, accepted, rejected, completed, cancelled
    message: Mapped[str | None] = mapped_column(Text)
    estimated_fee: Mapped[int] = mapped_column(Integer, default=2)  # credits
    card_price_at_interest: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("ix_trade_interest_buyer", "buyer_user_id"),
        Index("ix_trade_interest_seller", "seller_user_id"),
        Index("ix_trade_interest_status", "status"),
    )


class PortfolioSnapshotRow(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_value_brl: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    priced_card_count: Mapped[int] = mapped_column(Integer, default=0)
    total_card_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("user_id", "snapshot_date", name="uq_portfolio_snapshot"),
        Index("ix_portfolio_snapshots_user_date", "user_id", "snapshot_date"),
    )


class TradeAgreementRow(Base):
    __tablename__ = "trade_agreements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trade_interest_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    buyer_confirmed: Mapped[int] = mapped_column(Integer, default=0)
    seller_confirmed: Mapped[int] = mapped_column(Integer, default=0)
    buyer_fee_charged: Mapped[int] = mapped_column(Integer, default=0)  # credits charged
    seller_fee_charged: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (Index("ix_trade_agreement_interest", "trade_interest_id"),)


class EvaluationEntryRow(Base):
    __tablename__ = "evaluation_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    card_name: Mapped[str] = mapped_column(String(500), nullable=False)
    set_code: Mapped[str | None] = mapped_column(String(20))
    collector_number: Mapped[str | None] = mapped_column(String(20))
    liga_url: Mapped[str | None] = mapped_column(String(1000))
    source_data_json: Mapped[str | None] = mapped_column(Text)
    price_at_add: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    card_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    __table_args__ = (
        Index("ix_evaluation_entries_user", "user_id"),
        Index("ix_evaluation_entries_card", "card_id"),
    )


class ErrorLogRow(Base):
    __tablename__ = "error_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID string
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # ERROR, CRITICAL, WARNING
    error_type: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    traceback: Mapped[str | None] = mapped_column(Text)
    module: Mapped[str | None] = mapped_column(String(300))
    function: Mapped[str | None] = mapped_column(String(200))
    line: Mapped[int | None] = mapped_column(Integer)
    request_method: Mapped[str | None] = mapped_column(String(10))
    request_path: Mapped[str | None] = mapped_column(String(500))
    request_user_id: Mapped[int | None] = mapped_column(Integer)
    request_id: Mapped[str | None] = mapped_column(String(36))
    request_params: Mapped[str | None] = mapped_column(Text)  # JSON string
    extra: Mapped[str | None] = mapped_column(Text)  # JSON string

    __table_args__ = (
        Index("ix_error_log_timestamp", "timestamp"),
        Index("ix_error_log_level", "level"),
    )

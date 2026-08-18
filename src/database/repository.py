from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from src.database.models import (
    Base,
    CardRow,
    CollectionErrorRow,
    PriceObservationRow,
    SourceCardRow,
)
from src.domain.models import CollectionError, HistoricalPrice, SourceCard


class Repository:
    def __init__(self, db_url: str = "sqlite:///tcg_market.db"):
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)

    def upsert_source_card(self, card: SourceCard) -> int:
        """Insert or update a source card. Returns the source_card id."""
        with Session(self.engine) as session:
            existing = session.execute(
                select(SourceCardRow).where(
                    SourceCardRow.source == card.source,
                    SourceCardRow.external_id == card.external_id,
                )
            ).scalar_one_or_none()

            if existing:
                if card.sku:
                    existing.sku = card.sku
                if card.url:
                    existing.url = card.url
                if card.identity:
                    existing.name_en = card.identity.name_en
                    existing.name_pt = card.identity.name_pt
                    existing.set_code = card.identity.set_code
                    existing.collector_number = card.identity.collector_number
                session.commit()
                return existing.id

            row = SourceCardRow(
                source=card.source,
                external_id=card.external_id,
                sku=card.sku,
                url=card.url,
                name_en=card.identity.name_en if card.identity else None,
                name_pt=card.identity.name_pt if card.identity else None,
                set_code=card.identity.set_code if card.identity else None,
                collector_number=card.identity.collector_number if card.identity else None,
            )
            session.add(row)
            session.commit()
            return row.id

    def upsert_card(self, card: SourceCard) -> int | None:
        """Insert or update a canonical card row. Returns card id."""
        if not card.identity or not card.identity.set_code or not card.identity.collector_number:
            return None

        with Session(self.engine) as session:
            existing = session.execute(
                select(CardRow).where(
                    CardRow.game == card.identity.game,
                    CardRow.set_code == card.identity.set_code,
                    CardRow.collector_number == card.identity.collector_number,
                )
            ).scalar_one_or_none()

            if existing:
                if card.identity.name_en:
                    existing.name_en = card.identity.name_en
                if card.identity.name_pt:
                    existing.name_pt = card.identity.name_pt
                session.commit()
                return existing.id

            row = CardRow(
                game=card.identity.game,
                name_en=card.identity.name_en,
                name_pt=card.identity.name_pt,
                set_code=card.identity.set_code,
                collector_number=card.identity.collector_number,
            )
            session.add(row)
            session.commit()
            return row.id

    def insert_price_observations(self, prices: list[HistoricalPrice]) -> int:
        """Insert price observations, skipping duplicates. Returns count inserted."""
        if not prices:
            return 0
        inserted = 0
        with Session(self.engine) as session:
            for p in prices:
                existing = session.execute(
                    select(PriceObservationRow.id).where(
                        PriceObservationRow.source == p.source,
                        PriceObservationRow.external_id == p.external_id,
                        PriceObservationRow.observed_at == p.observed_at,
                    )
                ).scalar_one_or_none()
                if existing:
                    continue
                row = PriceObservationRow(
                    source=p.source,
                    external_id=p.external_id,
                    observed_at=p.observed_at,
                    median_price=p.median_price,
                    tcg_price=p.tcg_price,
                    last_sold_price=p.last_sold_price,
                    quantity_available=p.quantity_available,
                    last_sold_meta=p.last_sold_meta,
                    currency=p.currency,
                )
                session.add(row)
                inserted += 1
            session.commit()
        return inserted

    def insert_error(self, error: CollectionError) -> None:
        with Session(self.engine) as session:
            row = CollectionErrorRow(
                source=error.source,
                external_id=error.external_id,
                url=error.url,
                error_type=error.error_type,
                error_message=error.error_message,
                http_status=error.http_status,
                attempt=error.attempt,
                timestamp=error.timestamp,
            )
            session.add(row)
            session.commit()

    def get_unresolved_errors(self, source: str | None = None) -> list[CollectionErrorRow]:
        with Session(self.engine) as session:
            stmt = select(CollectionErrorRow).where(CollectionErrorRow.resolved == 0)
            if source:
                stmt = stmt.where(CollectionErrorRow.source == source)
            return list(session.execute(stmt).scalars().all())

    def mark_errors_resolved(self, source: str, external_id: str) -> None:
        with Session(self.engine) as session:
            rows = session.execute(
                select(CollectionErrorRow).where(
                    CollectionErrorRow.source == source,
                    CollectionErrorRow.external_id == external_id,
                    CollectionErrorRow.resolved == 0,
                )
            ).scalars().all()
            for r in rows:
                r.resolved = 1
            session.commit()

    def get_all_source_cards(self, source: str) -> list[SourceCardRow]:
        with Session(self.engine) as session:
            return list(
                session.execute(
                    select(SourceCardRow).where(SourceCardRow.source == source)
                ).scalars().all()
            )

    def get_price_series(
        self, source: str, external_id: str, days: int | None = None
    ) -> list[HistoricalPrice]:
        """Return price observations ordered by date ASC.

        If days is set, filter to last N days from today.
        """
        with Session(self.engine) as session:
            stmt = (
                select(PriceObservationRow)
                .where(
                    PriceObservationRow.source == source,
                    PriceObservationRow.external_id == external_id,
                )
                .order_by(PriceObservationRow.observed_at.asc())
            )
            if days is not None:
                cutoff = date.today() - timedelta(days=days)
                stmt = stmt.where(PriceObservationRow.observed_at >= cutoff)
            rows = session.execute(stmt).scalars().all()
            return [
                HistoricalPrice(
                    source=r.source,
                    external_id=r.external_id,
                    observed_at=r.observed_at,
                    median_price=r.median_price,
                    tcg_price=r.tcg_price,
                    last_sold_price=r.last_sold_price,
                    quantity_available=r.quantity_available,
                    last_sold_meta=r.last_sold_meta,
                    currency=r.currency,
                )
                for r in rows
            ]

    def get_cards_with_observations(self, source: str) -> list[tuple[str, int]]:
        """Return (external_id, observation_count) for cards with data."""
        with Session(self.engine) as session:
            stmt = (
                select(
                    PriceObservationRow.external_id,
                    func.count(PriceObservationRow.id).label("obs_count"),
                )
                .where(PriceObservationRow.source == source)
                .group_by(PriceObservationRow.external_id)
                .order_by(PriceObservationRow.external_id)
            )
            results = session.execute(stmt).all()
            return [(row[0], row[1]) for row in results]

    def get_observation_count(self, source: str | None = None) -> int:
        with Session(self.engine) as session:
            stmt = select(func.count()).select_from(PriceObservationRow)
            if source:
                stmt = stmt.where(PriceObservationRow.source == source)
            return session.execute(stmt).scalar() or 0

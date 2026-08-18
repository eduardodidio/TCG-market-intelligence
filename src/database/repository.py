from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
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

    def upsert_source_card(self, card: SourceCard, card_id: int | None = None) -> int:
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
                if card_id is not None:
                    existing.card_id = card_id
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
                card_id=card_id,
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
            for batch_start in range(0, len(prices), 500):
                batch = prices[batch_start : batch_start + 500]
                for p in batch:
                    stmt = (
                        sqlite_insert(PriceObservationRow)
                        .values(
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
                        .on_conflict_do_nothing(
                            index_elements=["source", "external_id", "observed_at"]
                        )
                    )
                    result = session.execute(stmt)
                    inserted += result.rowcount
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
            rows = (
                session.execute(
                    select(CollectionErrorRow).where(
                        CollectionErrorRow.source == source,
                        CollectionErrorRow.external_id == external_id,
                        CollectionErrorRow.resolved == 0,
                    )
                )
                .scalars()
                .all()
            )
            for r in rows:
                r.resolved = 1
            session.commit()

    def link_orphan_source_cards(self) -> int:
        """Link source_cards with card_id=NULL to their canonical card.

        Matches on (game, set_code, collector_number). Returns count linked.
        """
        linked = 0
        with Session(self.engine) as session:
            orphans = (
                session.execute(select(SourceCardRow).where(SourceCardRow.card_id.is_(None)))
                .scalars()
                .all()
            )
            for sc in orphans:
                if not sc.set_code or not sc.collector_number:
                    continue
                card = session.execute(
                    select(CardRow).where(
                        CardRow.game == "magic",
                        CardRow.set_code == sc.set_code,
                        CardRow.collector_number == sc.collector_number,
                    )
                ).scalar_one_or_none()
                if card:
                    sc.card_id = card.id
                    linked += 1
            session.commit()
        return linked

    def get_all_source_cards(self, source: str) -> list[SourceCardRow]:
        with Session(self.engine) as session:
            return list(
                session.execute(select(SourceCardRow).where(SourceCardRow.source == source))
                .scalars()
                .all()
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

    def list_cards(
        self,
        game: str | None = None,
        set_code: str | None = None,
        name_search: str | None = None,
        after_id: int | None = None,
        limit: int = 50,
    ) -> list[CardRow]:
        """List cards with optional filters and cursor pagination."""
        with Session(self.engine) as session:
            stmt = select(CardRow).order_by(CardRow.id.asc())
            if game:
                stmt = stmt.where(CardRow.game == game)
            if set_code:
                stmt = stmt.where(CardRow.set_code == set_code)
            if name_search:
                stmt = stmt.where(CardRow.name_en.ilike(f"%{name_search}%"))
            if after_id:
                stmt = stmt.where(CardRow.id > after_id)
            stmt = stmt.limit(limit + 1)
            return list(session.execute(stmt).scalars().all())

    def count_cards(
        self,
        game: str | None = None,
        set_code: str | None = None,
        name_search: str | None = None,
    ) -> int:
        """Count cards matching filters."""
        with Session(self.engine) as session:
            stmt = select(func.count()).select_from(CardRow)
            if game:
                stmt = stmt.where(CardRow.game == game)
            if set_code:
                stmt = stmt.where(CardRow.set_code == set_code)
            if name_search:
                stmt = stmt.where(CardRow.name_en.ilike(f"%{name_search}%"))
            return session.execute(stmt).scalar() or 0

    def get_card_by_id(self, card_id: int) -> CardRow | None:
        """Get a single card by ID."""
        with Session(self.engine) as session:
            return session.execute(
                select(CardRow).where(CardRow.id == card_id)
            ).scalar_one_or_none()

    def get_source_cards_for_card(self, card_id: int) -> list[SourceCardRow]:
        """Get all source cards linked to a canonical card."""
        with Session(self.engine) as session:
            return list(
                session.execute(select(SourceCardRow).where(SourceCardRow.card_id == card_id))
                .scalars()
                .all()
            )

    def get_latest_prices_batch(self, card_ids: list[int]) -> dict[int, PriceObservationRow | None]:
        """Get the latest price observation for each card_id."""
        if not card_ids:
            return {}
        with Session(self.engine) as session:
            result: dict[int, PriceObservationRow | None] = {}
            for card_id in card_ids:
                source_cards = (
                    session.execute(select(SourceCardRow).where(SourceCardRow.card_id == card_id))
                    .scalars()
                    .all()
                )
                latest = None
                for sc in source_cards:
                    obs = session.execute(
                        select(PriceObservationRow)
                        .where(
                            PriceObservationRow.source == sc.source,
                            PriceObservationRow.external_id == sc.external_id,
                        )
                        .order_by(PriceObservationRow.observed_at.desc())
                        .limit(1)
                    ).scalar_one_or_none()
                    if obs and (latest is None or obs.observed_at > latest.observed_at):
                        latest = obs
                result[card_id] = latest
            return result

    def list_sets(self, game: str | None = None) -> list[tuple[str, str, int]]:
        """List distinct sets with card counts."""
        with Session(self.engine) as session:
            stmt = (
                select(
                    CardRow.game,
                    CardRow.set_code,
                    func.count(CardRow.id).label("card_count"),
                )
                .where(CardRow.set_code.isnot(None))
                .group_by(CardRow.game, CardRow.set_code)
                .order_by(CardRow.game, CardRow.set_code)
            )
            if game:
                stmt = stmt.where(CardRow.game == game)
            results = session.execute(stmt).all()
            return [(r[0], r[1], r[2]) for r in results]

    def get_movers(self, days: int, limit: int = 10) -> tuple[list[tuple], list[tuple]]:
        """Get top price gainers and losers over a period.

        Returns (gainers, losers) as lists of tuples:
        (card_id, name_en, set_code, price_start, price_end, change_pct)
        """
        from decimal import Decimal

        cutoff = date.today() - timedelta(days=days)

        with Session(self.engine) as session:
            cards = session.execute(select(CardRow)).scalars().all()

            movers: list[tuple] = []
            for card in cards:
                source_cards = (
                    session.execute(select(SourceCardRow).where(SourceCardRow.card_id == card.id))
                    .scalars()
                    .all()
                )

                if not source_cards:
                    continue

                earliest_price = None
                latest_price = None

                for sc in source_cards:
                    early = session.execute(
                        select(PriceObservationRow)
                        .where(
                            PriceObservationRow.source == sc.source,
                            PriceObservationRow.external_id == sc.external_id,
                            PriceObservationRow.observed_at >= cutoff,
                            PriceObservationRow.median_price.isnot(None),
                        )
                        .order_by(PriceObservationRow.observed_at.asc())
                        .limit(1)
                    ).scalar_one_or_none()

                    late = session.execute(
                        select(PriceObservationRow)
                        .where(
                            PriceObservationRow.source == sc.source,
                            PriceObservationRow.external_id == sc.external_id,
                            PriceObservationRow.median_price.isnot(None),
                        )
                        .order_by(PriceObservationRow.observed_at.desc())
                        .limit(1)
                    ).scalar_one_or_none()

                    if early and late and early.median_price and late.median_price:
                        earliest_price = early.median_price
                        latest_price = late.median_price

                if earliest_price and latest_price and earliest_price != Decimal("0"):
                    change_pct = ((latest_price - earliest_price) / earliest_price) * 100
                    movers.append(
                        (
                            card.id,
                            card.name_en,
                            card.set_code,
                            earliest_price,
                            latest_price,
                            change_pct,
                        )
                    )

            gainers = sorted(movers, key=lambda x: x[5], reverse=True)[:limit]
            losers = sorted(movers, key=lambda x: x[5])[:limit]

            return gainers, losers

    def get_market_stats(self, game: str | None = None) -> dict:
        """Get aggregate market statistics."""
        with Session(self.engine) as session:
            card_stmt = select(func.count()).select_from(CardRow)
            if game:
                card_stmt = card_stmt.where(CardRow.game == game)
            total_cards = session.execute(card_stmt).scalar() or 0

            total_obs = (
                session.execute(select(func.count()).select_from(PriceObservationRow)).scalar() or 0
            )

            date_range = session.execute(
                select(
                    func.min(PriceObservationRow.observed_at),
                    func.max(PriceObservationRow.observed_at),
                )
            ).one()

            avg_price = session.execute(
                select(func.avg(PriceObservationRow.median_price)).where(
                    PriceObservationRow.median_price.isnot(None)
                )
            ).scalar()

            return {
                "total_cards": total_cards,
                "total_observations": total_obs,
                "avg_price": avg_price,
                "date_range_start": date_range[0],
                "date_range_end": date_range[1],
            }

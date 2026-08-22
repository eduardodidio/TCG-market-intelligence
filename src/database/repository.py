from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.database.models import (
    Base,
    CardLegalityRow,
    CardRow,
    CollectionErrorRow,
    DeckCardRow,
    DeckRow,
    ExchangeRateRow,
    LegalityHistoryRow,
    PriceObservationRow,
    ScanRunRow,
    ScheduledScanRow,
    SourceCardRow,
    UserCollectionRow,
    UserRow,
)
from src.domain.models import (
    CardLegality,
    CollectionError,
    ExchangeRate,
    HistoricalPrice,
    LegalityChange,
    ScanFilter,
    SourceCard,
)


class Repository:
    def __init__(self, db_url: str = "sqlite:///tcg_market.db"):
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self._ensure_columns()

    def _ensure_columns(self) -> None:
        """Add missing columns to existing tables (SQLite migration)."""
        insp = inspect(self.engine)
        if "users" in insp.get_table_names():
            columns = {col["name"] for col in insp.get_columns("users")}
            if "preferred_language" not in columns:
                with self.engine.begin() as conn:
                    sql = "ALTER TABLE users ADD COLUMN preferred_language VARCHAR(10) DEFAULT 'en'"
                    conn.execute(text(sql))

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

    def create_canonical_card(
        self,
        game: str,
        name_en: str,
        name_pt: str | None,
        set_code: str,
        collector_number: str,
    ) -> int:
        """Create or find a canonical card row from basic fields. Returns card id."""
        with Session(self.engine) as session:
            existing = session.execute(
                select(CardRow).where(
                    CardRow.game == game,
                    CardRow.set_code == set_code,
                    CardRow.collector_number == collector_number,
                )
            ).scalar_one_or_none()

            if existing:
                if name_en and not existing.name_en:
                    existing.name_en = name_en
                if name_pt and not existing.name_pt:
                    existing.name_pt = name_pt
                session.commit()
                return existing.id

            row = CardRow(
                game=game,
                name_en=name_en,
                name_pt=name_pt,
                set_code=set_code,
                collector_number=collector_number,
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
        self, source: str | list[str], external_id: str, days: int | None = None
    ) -> list[HistoricalPrice]:
        """Return price observations ordered by date ASC.

        ``source`` may be a single string or a list of strings.
        If days is set, filter to last N days from today.
        """
        with Session(self.engine) as session:
            if isinstance(source, list):
                source_filter = PriceObservationRow.source.in_(source)
            else:
                source_filter = PriceObservationRow.source == source
            stmt = (
                select(PriceObservationRow)
                .where(
                    source_filter,
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
                            PriceObservationRow.source.in_([sc.source, "jsonld_snapshot"]),
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
        (card_id, name_en, name_pt, set_code, price_start, price_end, change_pct)
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
                            PriceObservationRow.source.in_([sc.source, "jsonld_snapshot"]),
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
                            PriceObservationRow.source.in_([sc.source, "jsonld_snapshot"]),
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
                            card.name_pt,
                            card.set_code,
                            earliest_price,
                            latest_price,
                            change_pct,
                        )
                    )

            gainers = sorted(movers, key=lambda x: x[6], reverse=True)[:limit]
            losers = sorted(movers, key=lambda x: x[6])[:limit]

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

    def get_latest_observation_date(self, source: str | None = None) -> date | None:
        """Return the most recent observation date, optionally filtered by source."""
        with Session(self.engine) as session:
            stmt = select(func.max(PriceObservationRow.observed_at))
            if source:
                stmt = stmt.where(PriceObservationRow.source == source)
            return session.execute(stmt).scalar()

    def get_stale_cards_count(self, source: str | None = None, stale_days: int = 14) -> int:
        """Count source cards whose latest observation is older than stale_days.

        Also counts source cards with zero observations as stale.
        """
        cutoff = date.today() - timedelta(days=stale_days)
        with Session(self.engine) as session:
            # Subquery: latest observation per (source, external_id)
            latest_obs = (
                select(
                    PriceObservationRow.source,
                    PriceObservationRow.external_id,
                    func.max(PriceObservationRow.observed_at).label("max_date"),
                )
                .group_by(PriceObservationRow.source, PriceObservationRow.external_id)
                .subquery()
            )

            # LEFT JOIN source_cards with latest observations
            stmt = (
                select(func.count())
                .select_from(SourceCardRow)
                .outerjoin(
                    latest_obs,
                    (SourceCardRow.source == latest_obs.c.source)
                    & (SourceCardRow.external_id == latest_obs.c.external_id),
                )
                .where((latest_obs.c.max_date < cutoff) | (latest_obs.c.max_date.is_(None)))
            )

            if source:
                stmt = stmt.where(SourceCardRow.source == source)

            return session.execute(stmt).scalar() or 0

    def get_recent_errors_count(self, source: str | None = None, days: int = 7) -> int:
        """Count unresolved collection errors from the last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        with Session(self.engine) as session:
            stmt = (
                select(func.count())
                .select_from(CollectionErrorRow)
                .where(
                    CollectionErrorRow.resolved == 0,
                    CollectionErrorRow.timestamp >= cutoff,
                )
            )
            if source:
                stmt = stmt.where(CollectionErrorRow.source == source)
            return session.execute(stmt).scalar() or 0

    def get_source_card_count(self, source: str | None = None) -> int:
        """Count total source cards, optionally filtered by source."""
        with Session(self.engine) as session:
            stmt = select(func.count()).select_from(SourceCardRow)
            if source:
                stmt = stmt.where(SourceCardRow.source == source)
            return session.execute(stmt).scalar() or 0

    # ── User Collection ──────────────────────────────────────────────

    def get_collection_entry(self, entry_id: int) -> UserCollectionRow | None:
        """Get a single user_collection entry by ID."""
        with Session(self.engine) as session:
            return session.execute(
                select(UserCollectionRow).where(UserCollectionRow.id == entry_id)
            ).scalar_one_or_none()

    def link_collection_entry(self, entry_id: int, card_id: int) -> None:
        """Set card_id on a user_collection entry."""
        with Session(self.engine) as session:
            entry = session.get(UserCollectionRow, entry_id)
            if entry:
                entry.card_id = card_id
                session.commit()

    def get_all_collection_entries(self) -> list[UserCollectionRow]:
        """Return all user_collection rows (all users). READ-ONLY helper
        used by the match-report CLI to iterate over the full collection."""
        with Session(self.engine) as session:
            return list(
                session.execute(select(UserCollectionRow).order_by(UserCollectionRow.id.asc()))
                .scalars()
                .all()
            )

    _COLLECTION_SORT_COLUMNS = {
        "name": "name_en",
        "set": "set_code",
        "number": "collector_number",
        "added": "created_at",
    }

    def list_collection(
        self,
        user_id: str,
        name_search: str | None = None,
        set_code: str | None = None,
        sort_by: str = "name",
        sort_dir: str = "asc",
        offset: int = 0,
        limit: int = 50,
        after_id: int | None = None,
    ) -> list[UserCollectionRow]:
        with Session(self.engine) as session:
            stmt = select(UserCollectionRow).where(UserCollectionRow.user_id == user_id)
            if name_search:
                pattern = f"%{name_search}%"
                stmt = stmt.where(
                    UserCollectionRow.name_en.ilike(pattern)
                    | UserCollectionRow.name_pt.ilike(pattern)
                )
            if set_code:
                stmt = stmt.where(UserCollectionRow.set_code == set_code)

            # Sorting
            col_name = self._COLLECTION_SORT_COLUMNS.get(sort_by, "name_en")
            col = getattr(UserCollectionRow, col_name)
            # Handle NULLs: coalesce nullable string columns to '' so they sort last
            if col_name in ("name_en",):
                sort_expr = func.coalesce(col, "")
            else:
                sort_expr = col
            if sort_dir == "desc":
                sort_expr = sort_expr.desc()
            else:
                sort_expr = sort_expr.asc()
            stmt = stmt.order_by(sort_expr, UserCollectionRow.id.asc())

            # Pagination: cursor-based (after_id) takes precedence over offset
            if after_id is not None:
                stmt = stmt.where(UserCollectionRow.id > after_id)
            elif offset:
                stmt = stmt.offset(offset)

            stmt = stmt.limit(limit + 1)
            return list(session.execute(stmt).scalars().all())

    def count_collection(
        self,
        user_id: str,
        name_search: str | None = None,
        set_code: str | None = None,
    ) -> int:
        with Session(self.engine) as session:
            stmt = (
                select(func.count())
                .select_from(UserCollectionRow)
                .where(UserCollectionRow.user_id == user_id)
            )
            if name_search:
                pattern = f"%{name_search}%"
                stmt = stmt.where(
                    UserCollectionRow.name_en.ilike(pattern)
                    | UserCollectionRow.name_pt.ilike(pattern)
                )
            if set_code:
                stmt = stmt.where(UserCollectionRow.set_code == set_code)
            return session.execute(stmt).scalar() or 0

    def get_collection_summary(self, user_id: str) -> dict:
        with Session(self.engine) as session:
            total_unique = (
                session.execute(
                    select(func.count())
                    .select_from(UserCollectionRow)
                    .where(UserCollectionRow.user_id == user_id)
                ).scalar()
                or 0
            )
            total_cards = (
                session.execute(
                    select(func.coalesce(func.sum(UserCollectionRow.quantity), 0)).where(
                        UserCollectionRow.user_id == user_id
                    )
                ).scalar()
                or 0
            )
            linked_count = (
                session.execute(
                    select(func.count())
                    .select_from(UserCollectionRow)
                    .where(
                        UserCollectionRow.user_id == user_id,
                        UserCollectionRow.card_id.isnot(None),
                    )
                ).scalar()
                or 0
            )
            sets_count = (
                session.execute(
                    select(func.count(func.distinct(UserCollectionRow.set_code))).where(
                        UserCollectionRow.user_id == user_id
                    )
                ).scalar()
                or 0
            )
            # Count linked entries that have at least one price observation
            priced_count = 0
            if linked_count > 0:
                priced_card_ids = (
                    select(func.distinct(SourceCardRow.card_id))
                    .join(
                        PriceObservationRow,
                        (PriceObservationRow.source == SourceCardRow.source)
                        & (PriceObservationRow.external_id == SourceCardRow.external_id),
                    )
                    .where(SourceCardRow.card_id.isnot(None))
                )
                priced_count = (
                    session.execute(
                        select(func.count())
                        .select_from(UserCollectionRow)
                        .where(
                            UserCollectionRow.user_id == user_id,
                            UserCollectionRow.card_id.isnot(None),
                            UserCollectionRow.card_id.in_(priced_card_ids),
                        )
                    ).scalar()
                    or 0
                )

            return {
                "total_unique": total_unique,
                "total_cards": int(total_cards),
                "linked_count": linked_count,
                "priced_count": priced_count,
                "sets_count": sets_count,
            }

    def get_collection_sets(self, user_id: str) -> list[tuple[str, str | None, int]]:
        """Return distinct (set_code, set_name_en, count) for a user's collection."""
        with Session(self.engine) as session:
            stmt = (
                select(
                    UserCollectionRow.set_code,
                    func.max(UserCollectionRow.set_name_en),
                    func.count(UserCollectionRow.id),
                )
                .where(UserCollectionRow.user_id == user_id)
                .group_by(UserCollectionRow.set_code)
                .order_by(UserCollectionRow.set_code)
            )
            return [(r[0], r[1], r[2]) for r in session.execute(stmt).all()]

    def get_collection_total_value(self, user_id: str) -> Decimal | None:
        """Calculate the total portfolio value for linked collection entries.

        Sums (median_price * quantity) for each linked card. Returns None
        if there are no linked cards or none of them have prices.
        """
        with Session(self.engine) as session:
            linked_rows = (
                session.execute(
                    select(UserCollectionRow).where(
                        UserCollectionRow.user_id == user_id,
                        UserCollectionRow.card_id.isnot(None),
                    )
                )
                .scalars()
                .all()
            )
            if not linked_rows:
                return None
            card_ids = list({r.card_id for r in linked_rows})
            prices = self.get_latest_prices_batch(card_ids)
            total = Decimal("0")
            for r in linked_rows:
                obs = prices.get(r.card_id)
                if obs and obs.median_price:
                    total += obs.median_price * r.quantity
            return total if total > 0 else None

    # ── Snapshot helpers ─────────────────────────────────────────

    def get_linked_collection_with_source(self, source: str = "myp") -> list[dict]:
        """Return linked collection entries with source_card info.

        Only returns entries where card_id IS NOT NULL and a matching
        source_card exists for the given source.

        Returns list of dicts with keys: entry_id, card_id,
        external_id, slug, url.
        """
        with Session(self.engine) as session:
            stmt = (
                select(
                    UserCollectionRow.id.label("entry_id"),
                    UserCollectionRow.card_id,
                    SourceCardRow.external_id,
                    SourceCardRow.url,
                )
                .join(
                    SourceCardRow,
                    SourceCardRow.card_id == UserCollectionRow.card_id,
                )
                .where(
                    UserCollectionRow.card_id.isnot(None),
                    SourceCardRow.source == source,
                )
                .order_by(UserCollectionRow.id.asc())
            )
            rows = session.execute(stmt).all()
            results = []
            for r in rows:
                url = r.url or ""
                slug = url.rsplit("/", 1)[-1] if "/" in url else ""
                results.append(
                    {
                        "entry_id": r.entry_id,
                        "card_id": r.card_id,
                        "external_id": r.external_id,
                        "slug": slug,
                        "url": url,
                    }
                )
            return results

    def has_snapshot_for_date(self, external_id: str, obs_date: date) -> bool:
        """Check if a jsonld_snapshot observation exists for this card+date."""
        with Session(self.engine) as session:
            stmt = (
                select(PriceObservationRow.id)
                .where(
                    PriceObservationRow.source == "jsonld_snapshot",
                    PriceObservationRow.external_id == external_id,
                    PriceObservationRow.observed_at == obs_date,
                )
                .limit(1)
            )
            return session.execute(stmt).scalar_one_or_none() is not None

    # ── Scan Runs ────────────────────────────────────────────────

    def create_scan_run(self, scan_type: str, filters_json: str = "{}") -> int:
        """Insert a new scan run row and return its ID."""
        with Session(self.engine) as session:
            row = ScanRunRow(scan_type=scan_type, filters_json=filters_json)
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.id

    def update_scan_run(self, run_id: int, **fields) -> None:
        """Update a scan run with the given fields."""
        from sqlalchemy import update

        with Session(self.engine) as session:
            stmt = update(ScanRunRow).where(ScanRunRow.id == run_id).values(**fields)
            session.execute(stmt)
            session.commit()

    def get_scan_run(self, run_id: int) -> dict | None:
        """Return a scan run as a dict, or None if not found."""
        with Session(self.engine) as session:
            row = session.execute(
                select(ScanRunRow).where(ScanRunRow.id == run_id)
            ).scalar_one_or_none()
            if row is None:
                return None
            return {
                "id": row.id,
                "scan_type": row.scan_type,
                "filters_json": row.filters_json,
                "status": row.status,
                "cards_total": row.cards_total,
                "cards_processed": row.cards_processed,
                "cards_failed": row.cards_failed,
                "observations_saved": row.observations_saved,
                "error_summary": row.error_summary,
                "started_at": row.started_at,
                "finished_at": row.finished_at,
                "created_at": row.created_at,
            }

    def list_scan_runs(
        self,
        limit: int = 20,
        offset: int = 0,
        scan_type: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        """List scan runs with optional filters, ordered by created_at desc."""
        with Session(self.engine) as session:
            stmt = select(ScanRunRow).order_by(ScanRunRow.created_at.desc())
            if scan_type is not None:
                stmt = stmt.where(ScanRunRow.scan_type == scan_type)
            if status is not None:
                stmt = stmt.where(ScanRunRow.status == status)
            stmt = stmt.offset(offset).limit(limit)
            rows = session.execute(stmt).scalars().all()
            return [
                {
                    "id": r.id,
                    "scan_type": r.scan_type,
                    "filters_json": r.filters_json,
                    "status": r.status,
                    "cards_total": r.cards_total,
                    "cards_processed": r.cards_processed,
                    "cards_failed": r.cards_failed,
                    "observations_saved": r.observations_saved,
                    "error_summary": r.error_summary,
                    "started_at": r.started_at,
                    "finished_at": r.finished_at,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    def get_cards_for_scan(self, scan_filter: ScanFilter) -> list[dict]:
        """Return cards matching the scan filter.

        Returns list of {external_id, slug, card_id, set_code, name_en}.
        """
        with Session(self.engine) as session:
            stmt = (
                select(
                    SourceCardRow.external_id,
                    SourceCardRow.url,
                    UserCollectionRow.card_id,
                    UserCollectionRow.set_code,
                    UserCollectionRow.name_en,
                )
                .join(
                    SourceCardRow,
                    SourceCardRow.card_id == UserCollectionRow.card_id,
                )
                .where(
                    UserCollectionRow.card_id.isnot(None),
                    SourceCardRow.source == "myp",
                )
                .order_by(UserCollectionRow.id.asc())
            )

            if scan_filter.set_codes:
                stmt = stmt.where(UserCollectionRow.set_code.in_(scan_filter.set_codes))
            if scan_filter.rarities:
                stmt = stmt.where(UserCollectionRow.rarity.in_(scan_filter.rarities))
            if scan_filter.card_ids:
                stmt = stmt.where(UserCollectionRow.card_id.in_(scan_filter.card_ids))
            if scan_filter.limit:
                stmt = stmt.limit(scan_filter.limit)

            rows = session.execute(stmt).all()
            results = []
            for r in rows:
                url = r.url or ""
                slug = url.rsplit("/", 1)[-1] if "/" in url else ""
                results.append(
                    {
                        "external_id": r.external_id,
                        "slug": slug,
                        "card_id": r.card_id,
                        "set_code": r.set_code,
                        "name_en": r.name_en,
                    }
                )
            return results

    # ── Exchange Rates ──────────────────────────────────────────

    def upsert_exchange_rate(self, rate: ExchangeRate) -> None:
        """Insert or update an exchange rate by rate_date."""
        with Session(self.engine) as session:
            stmt = (
                sqlite_insert(ExchangeRateRow)
                .values(
                    rate_date=rate.rate_date,
                    from_currency=rate.from_currency,
                    to_currency=rate.to_currency,
                    rate=rate.rate,
                    source=rate.source,
                )
                .on_conflict_do_update(
                    index_elements=["rate_date"],
                    set_={
                        "rate": rate.rate,
                        "from_currency": rate.from_currency,
                        "to_currency": rate.to_currency,
                        "source": rate.source,
                    },
                )
            )
            session.execute(stmt)
            session.commit()

    def get_exchange_rate(self, rate_date: date) -> ExchangeRateRow | None:
        """Get an exchange rate for an exact date."""
        with Session(self.engine) as session:
            return session.execute(
                select(ExchangeRateRow).where(ExchangeRateRow.rate_date == rate_date)
            ).scalar_one_or_none()

    def get_closest_rate(self, target_date: date) -> ExchangeRateRow | None:
        """Get the closest exchange rate on or before target_date."""
        with Session(self.engine) as session:
            return session.execute(
                select(ExchangeRateRow)
                .where(ExchangeRateRow.rate_date <= target_date)
                .order_by(ExchangeRateRow.rate_date.desc())
                .limit(1)
            ).scalar_one_or_none()

    def get_latest_rate(self) -> ExchangeRateRow | None:
        """Get the most recent exchange rate."""
        with Session(self.engine) as session:
            return session.execute(
                select(ExchangeRateRow).order_by(ExchangeRateRow.rate_date.desc()).limit(1)
            ).scalar_one_or_none()

    def get_rate_history(self, days: int = 30) -> list[ExchangeRateRow]:
        """Get exchange rates for the last N days."""
        cutoff = date.today() - timedelta(days=days)
        with Session(self.engine) as session:
            return list(
                session.execute(
                    select(ExchangeRateRow)
                    .where(ExchangeRateRow.rate_date >= cutoff)
                    .order_by(ExchangeRateRow.rate_date.desc())
                )
                .scalars()
                .all()
            )

    def bulk_upsert_rates(self, rates: list[ExchangeRate]) -> None:
        """Bulk insert or update exchange rates."""
        for rate in rates:
            self.upsert_exchange_rate(rate)

    # ── Users ───────────────────────────────────────────────────────

    def create_user(
        self,
        email: str,
        display_name: str | None = None,
        auth_provider: str = "email",
        provider_id: str | None = None,
        password_hash: str | None = None,
    ) -> UserRow:
        """Create a new user. Returns the created UserRow."""
        with Session(self.engine) as session:
            user = UserRow(
                email=email,
                display_name=display_name,
                auth_provider=auth_provider,
                provider_id=provider_id,
                password_hash=password_hash,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            # Expunge so the object is usable outside the session
            session.expunge(user)
            return user

    def get_user_by_id(self, user_id: int) -> UserRow | None:
        """Get a user by ID."""
        with Session(self.engine) as session:
            user = session.execute(
                select(UserRow).where(UserRow.id == user_id)
            ).scalar_one_or_none()
            if user:
                session.expunge(user)
            return user

    def get_user_by_email(self, email: str) -> UserRow | None:
        """Get a user by email address."""
        with Session(self.engine) as session:
            user = session.execute(
                select(UserRow).where(UserRow.email == email)
            ).scalar_one_or_none()
            if user:
                session.expunge(user)
            return user

    def get_user_by_provider(self, provider: str, provider_id: str) -> UserRow | None:
        """Get a user by OAuth provider and provider ID."""
        with Session(self.engine) as session:
            user = session.execute(
                select(UserRow).where(
                    UserRow.auth_provider == provider,
                    UserRow.provider_id == provider_id,
                )
            ).scalar_one_or_none()
            if user:
                session.expunge(user)
            return user

    def update_user(self, user_id: int, **kwargs) -> UserRow | None:
        """Update a user with the given fields. Returns updated UserRow or None."""
        with Session(self.engine) as session:
            user = session.execute(
                select(UserRow).where(UserRow.id == user_id)
            ).scalar_one_or_none()
            if user is None:
                return None
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            session.commit()
            session.refresh(user)
            session.expunge(user)
            return user

    def migrate_collection_user(self, old_user_id: str, new_user_id: str) -> int:
        """Migrate collection entries from old_user_id to new_user_id.

        Returns the number of rows updated.
        """
        from sqlalchemy import update

        with Session(self.engine) as session:
            result = session.execute(
                update(UserCollectionRow)
                .where(UserCollectionRow.user_id == old_user_id)
                .values(user_id=new_user_id)
            )
            session.commit()
            return result.rowcount

    # --- Deck methods ---

    def create_deck(self, user_id: str, name: str, description: str | None = None) -> DeckRow:
        """Create a new deck and return it."""
        with Session(self.engine) as session:
            deck = DeckRow(user_id=user_id, name=name, description=description)
            session.add(deck)
            session.commit()
            session.refresh(deck)
            session.expunge(deck)
            return deck

    def add_deck_cards(self, deck_id: int, cards: list[dict]) -> int:
        """Bulk insert cards into a deck. Returns the count inserted."""
        if not cards:
            return 0
        with Session(self.engine) as session:
            rows = []
            for c in cards:
                rows.append(
                    DeckCardRow(
                        deck_id=deck_id,
                        name_en=c["name_en"],
                        set_code=c.get("set_code"),
                        collector_number=c.get("collector_number"),
                        quantity=c.get("quantity", 1),
                        card_id=c.get("card_id"),
                    )
                )
            session.add_all(rows)
            session.commit()
            return len(rows)

    def get_deck(self, deck_id: int) -> DeckRow | None:
        """Get a single deck by ID."""
        with Session(self.engine) as session:
            deck = session.execute(
                select(DeckRow).where(DeckRow.id == deck_id)
            ).scalar_one_or_none()
            if deck:
                session.expunge(deck)
            return deck

    def list_decks(self, user_id: str) -> list[DeckRow]:
        """List all decks for a user, newest first."""
        with Session(self.engine) as session:
            rows = (
                session.execute(
                    select(DeckRow)
                    .where(DeckRow.user_id == user_id)
                    .order_by(DeckRow.created_at.desc())
                )
                .scalars()
                .all()
            )
            for r in rows:
                session.expunge(r)
            return list(rows)

    def delete_deck(self, deck_id: int, user_id: str) -> bool:
        """Delete a deck and its cards. Only if user_id matches.

        Returns True if the deck was deleted, False otherwise.
        """
        with Session(self.engine) as session:
            deck = session.execute(
                select(DeckRow).where(DeckRow.id == deck_id, DeckRow.user_id == user_id)
            ).scalar_one_or_none()
            if not deck:
                return False
            # Delete cards first
            session.query(DeckCardRow).filter(DeckCardRow.deck_id == deck_id).delete()
            session.delete(deck)
            session.commit()
            return True

    def get_deck_cards(self, deck_id: int) -> list[DeckCardRow]:
        """Get all cards for a deck."""
        with Session(self.engine) as session:
            rows = (
                session.execute(select(DeckCardRow).where(DeckCardRow.deck_id == deck_id))
                .scalars()
                .all()
            )
            for r in rows:
                session.expunge(r)
            return list(rows)

    def get_deck_cards_with_ownership(self, deck_id: int, user_id: str) -> list[dict]:
        """Get deck cards with ownership info from user_collection.

        Uses 3-tier matching:
        (a) card_id match
        (b) set_code + collector_number match
        (c) name_en case-insensitive match
        """
        with Session(self.engine) as session:
            deck_cards = (
                session.execute(select(DeckCardRow).where(DeckCardRow.deck_id == deck_id))
                .scalars()
                .all()
            )

            # Pre-load user collection for matching
            collection = (
                session.execute(
                    select(UserCollectionRow).where(UserCollectionRow.user_id == user_id)
                )
                .scalars()
                .all()
            )

            # Build lookup indexes
            by_card_id: dict[int, UserCollectionRow] = {}
            by_set_num: dict[tuple[str, str], UserCollectionRow] = {}
            by_name: dict[str, list[UserCollectionRow]] = {}
            for uc in collection:
                if uc.card_id is not None:
                    by_card_id[uc.card_id] = uc
                if uc.set_code and uc.collector_number:
                    by_set_num[(uc.set_code.lower(), uc.collector_number.lower())] = uc
                if uc.name_en:
                    key = uc.name_en.lower()
                    by_name.setdefault(key, []).append(uc)

            results = []
            for dc in deck_cards:
                match: UserCollectionRow | None = None

                # Tier (a): card_id match
                if dc.card_id is not None and dc.card_id in by_card_id:
                    match = by_card_id[dc.card_id]

                # Tier (b): set_code + collector_number
                if match is None and dc.set_code and dc.collector_number:
                    key = (dc.set_code.lower(), dc.collector_number.lower())
                    if key in by_set_num:
                        match = by_set_num[key]

                # Tier (c): name_en case-insensitive
                if match is None and dc.name_en:
                    candidates = by_name.get(dc.name_en.lower(), [])
                    if len(candidates) == 1:
                        match = candidates[0]

                results.append(
                    {
                        "id": dc.id,
                        "deck_id": dc.deck_id,
                        "name_en": dc.name_en,
                        "set_code": dc.set_code,
                        "collector_number": dc.collector_number,
                        "quantity": dc.quantity,
                        "card_id": dc.card_id,
                        "in_collection": match is not None,
                        "owned_quantity": match.quantity if match else 0,
                        "collection_entry_id": match.id if match else None,
                    }
                )

            return results

    def get_deck_summary(self, deck_id: int, user_id: str) -> dict:
        """Get aggregated deck summary with ownership stats."""
        cards_with_ownership = self.get_deck_cards_with_ownership(deck_id, user_id)
        total_cards = sum(c["quantity"] for c in cards_with_ownership)
        unique_cards = len(cards_with_ownership)
        owned_cards = sum(1 for c in cards_with_ownership if c["in_collection"])
        ownership_pct = round(owned_cards / unique_cards * 100, 2) if unique_cards > 0 else 0.0
        return {
            "total_cards": total_cards,
            "unique_cards": unique_cards,
            "owned_cards": owned_cards,
            "ownership_pct": ownership_pct,
        }

    def link_deck_card(self, deck_card_id: int, card_id: int) -> None:
        """Link a deck card to a canonical card."""
        from sqlalchemy import update

        with Session(self.engine) as session:
            session.execute(
                update(DeckCardRow).where(DeckCardRow.id == deck_card_id).values(card_id=card_id)
            )
            session.commit()

    # --- Legality / ban list methods ---

    def upsert_legalities(self, legalities: list[CardLegality]) -> int:
        """Bulk upsert card legalities. Returns count of rows affected."""
        if not legalities:
            return 0
        with Session(self.engine) as session:
            count = 0
            for leg in legalities:
                stmt = sqlite_insert(CardLegalityRow).values(
                    card_id=leg.card_id,
                    format=leg.format,
                    status=leg.status,
                    effective_date=leg.effective_date,
                    updated_at=datetime.now(),
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["card_id", "format"],
                    set_={
                        "status": stmt.excluded.status,
                        "effective_date": stmt.excluded.effective_date,
                        "updated_at": stmt.excluded.updated_at,
                    },
                )
                session.execute(stmt)
                count += 1
            session.commit()
            return count

    def insert_legality_changes(self, changes: list[LegalityChange]) -> int:
        """Bulk insert legality change history. Returns count inserted."""
        if not changes:
            return 0
        with Session(self.engine) as session:
            rows = [
                LegalityHistoryRow(
                    card_id=c.card_id,
                    format=c.format,
                    old_status=c.old_status,
                    new_status=c.new_status,
                    changed_at=c.changed_at,
                    source=c.source,
                )
                for c in changes
            ]
            session.add_all(rows)
            session.commit()
            return len(rows)

    def get_legalities_by_format(
        self,
        format: str,
        status: str | None = None,
        search: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        """Get legalities for a format, joined with card info."""
        with Session(self.engine) as session:
            stmt = (
                select(
                    CardLegalityRow.card_id,
                    CardLegalityRow.format,
                    CardLegalityRow.status,
                    CardLegalityRow.effective_date,
                    CardRow.name_en,
                    CardRow.name_pt,
                    CardRow.set_code,
                    CardRow.collector_number,
                )
                .join(CardRow, CardRow.id == CardLegalityRow.card_id)
                .where(CardLegalityRow.format == format)
            )
            if status:
                stmt = stmt.where(CardLegalityRow.status == status)
            if search:
                pattern = f"%{search}%"
                stmt = stmt.where(CardRow.name_en.ilike(pattern) | CardRow.name_pt.ilike(pattern))
            stmt = stmt.order_by(CardRow.name_en).offset(offset).limit(limit)
            rows = session.execute(stmt).all()
            return [
                {
                    "card_id": r.card_id,
                    "format": r.format,
                    "status": r.status,
                    "effective_date": r.effective_date,
                    "name_en": r.name_en,
                    "name_pt": r.name_pt,
                    "set_code": r.set_code,
                    "collector_number": r.collector_number,
                }
                for r in rows
            ]

    def get_legalities_for_card(self, card_id: int) -> list[dict]:
        """All format legalities for a given card."""
        with Session(self.engine) as session:
            stmt = (
                select(CardLegalityRow)
                .where(CardLegalityRow.card_id == card_id)
                .order_by(CardLegalityRow.format)
            )
            rows = session.execute(stmt).scalars().all()
            return [
                {
                    "format": r.format,
                    "status": r.status,
                    "effective_date": r.effective_date,
                }
                for r in rows
            ]

    def get_legality_history(
        self,
        card_id: int | None = None,
        format: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get legality change history with optional filters."""
        with Session(self.engine) as session:
            stmt = select(
                LegalityHistoryRow.card_id,
                LegalityHistoryRow.format,
                LegalityHistoryRow.old_status,
                LegalityHistoryRow.new_status,
                LegalityHistoryRow.changed_at,
                CardRow.name_en,
            ).join(CardRow, CardRow.id == LegalityHistoryRow.card_id)
            if card_id is not None:
                stmt = stmt.where(LegalityHistoryRow.card_id == card_id)
            if format is not None:
                stmt = stmt.where(LegalityHistoryRow.format == format)
            stmt = stmt.order_by(LegalityHistoryRow.changed_at.desc()).limit(limit)
            rows = session.execute(stmt).all()
            return [
                {
                    "card_id": r.card_id,
                    "name_en": r.name_en,
                    "format": r.format,
                    "old_status": r.old_status,
                    "new_status": r.new_status,
                    "changed_at": r.changed_at,
                }
                for r in rows
            ]

    def get_known_formats(self) -> list[str]:
        """Get distinct formats from card_legalities."""
        with Session(self.engine) as session:
            stmt = select(CardLegalityRow.format).distinct().order_by(CardLegalityRow.format)
            return [r[0] for r in session.execute(stmt).all()]

    def get_legalities_for_cards_batch(self, card_ids: list[int]) -> dict[int, list[dict]]:
        """Batch fetch legalities for multiple cards."""
        if not card_ids:
            return {}
        with Session(self.engine) as session:
            stmt = (
                select(CardLegalityRow)
                .where(CardLegalityRow.card_id.in_(card_ids))
                .order_by(CardLegalityRow.card_id, CardLegalityRow.format)
            )
            rows = session.execute(stmt).scalars().all()
            result: dict[int, list[dict]] = {}
            for r in rows:
                result.setdefault(r.card_id, []).append(
                    {
                        "format": r.format,
                        "status": r.status,
                        "effective_date": r.effective_date,
                    }
                )
            return result

    def get_legality_history_paginated(
        self,
        card_id: int | None = None,
        format: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Get paginated legality change history with date filters and card info."""
        with Session(self.engine) as session:
            base = select(
                LegalityHistoryRow.id,
                LegalityHistoryRow.card_id,
                LegalityHistoryRow.format,
                LegalityHistoryRow.old_status,
                LegalityHistoryRow.new_status,
                LegalityHistoryRow.changed_at,
                LegalityHistoryRow.source,
                CardRow.name_en,
                CardRow.name_pt,
                CardRow.set_code,
                CardRow.collector_number,
            ).join(CardRow, CardRow.id == LegalityHistoryRow.card_id)
            if card_id is not None:
                base = base.where(LegalityHistoryRow.card_id == card_id)
            if format is not None:
                base = base.where(LegalityHistoryRow.format == format)
            if date_from is not None:
                dt_from = datetime.combine(date_from, datetime.min.time())
                base = base.where(LegalityHistoryRow.changed_at >= dt_from)
            if date_to is not None:
                dt_to = datetime.combine(date_to, datetime.max.time())
                base = base.where(LegalityHistoryRow.changed_at <= dt_to)

            # Total count (same filters, no limit/offset)
            count_stmt = select(func.count()).select_from(base.subquery())
            total = session.execute(count_stmt).scalar() or 0

            # Paginated results
            stmt = base.order_by(LegalityHistoryRow.changed_at.desc()).offset(offset).limit(limit)
            rows = session.execute(stmt).all()
            items = [
                {
                    "id": r.id,
                    "card_id": r.card_id,
                    "name_en": r.name_en,
                    "name_pt": r.name_pt,
                    "set_code": r.set_code,
                    "collector_number": r.collector_number,
                    "format": r.format,
                    "old_status": r.old_status,
                    "new_status": r.new_status,
                    "changed_at": r.changed_at,
                    "source": r.source,
                }
                for r in rows
            ]
            return items, total

    def get_card_ban_history(self, card_id: int) -> list[dict]:
        """Get all legality history for a specific card (all formats)."""
        with Session(self.engine) as session:
            stmt = (
                select(LegalityHistoryRow)
                .where(LegalityHistoryRow.card_id == card_id)
                .order_by(LegalityHistoryRow.changed_at.desc(), LegalityHistoryRow.format)
            )
            rows = session.execute(stmt).scalars().all()
            return [
                {
                    "id": r.id,
                    "format": r.format,
                    "old_status": r.old_status,
                    "new_status": r.new_status,
                    "changed_at": r.changed_at,
                    "source": r.source,
                }
                for r in rows
            ]

    def get_ban_events_for_impact(self, card_id: int) -> list[dict]:
        """Get ban/unban transition events for impact analysis."""
        ban_statuses = {"banned", "restricted"}
        with Session(self.engine) as session:
            stmt = (
                select(LegalityHistoryRow)
                .where(LegalityHistoryRow.card_id == card_id)
                .where(
                    LegalityHistoryRow.new_status.in_(ban_statuses)
                    | LegalityHistoryRow.old_status.in_(ban_statuses)
                )
                .order_by(LegalityHistoryRow.changed_at.asc())
            )
            rows = session.execute(stmt).scalars().all()
            return [
                {
                    "id": r.id,
                    "format": r.format,
                    "old_status": r.old_status,
                    "new_status": r.new_status,
                    "changed_at": r.changed_at,
                    "source": r.source,
                }
                for r in rows
            ]

    # --- Scheduled scan methods ---

    def _scheduled_scan_to_dict(self, row: ScheduledScanRow) -> dict:
        """Convert a ScheduledScanRow to a plain dict."""
        return {
            "id": row.id,
            "user_id": row.user_id,
            "name": row.name,
            "description": row.description,
            "cron_expression": row.cron_expression,
            "scan_type": row.scan_type,
            "filters_json": row.filters_json,
            "status": row.status,
            "last_run_id": row.last_run_id,
            "last_run_at": row.last_run_at,
            "next_run_at": row.next_run_at,
            "error_count": row.error_count,
            "max_retries": row.max_retries,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def create_scheduled_scan(
        self,
        user_id: str,
        name: str,
        cron_expression: str,
        scan_type: str,
        filters_json: str = "{}",
        description: str | None = None,
        max_retries: int = 3,
    ) -> int:
        """Insert a new scheduled scan and return its ID."""
        with Session(self.engine) as session:
            row = ScheduledScanRow(
                user_id=user_id,
                name=name,
                cron_expression=cron_expression,
                scan_type=scan_type,
                filters_json=filters_json,
                description=description,
                max_retries=max_retries,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.id

    def get_scheduled_scan(self, schedule_id: int) -> dict | None:
        """Get a single scheduled scan by ID."""
        with Session(self.engine) as session:
            row = session.execute(
                select(ScheduledScanRow).where(ScheduledScanRow.id == schedule_id)
            ).scalar_one_or_none()
            if row is None:
                return None
            return self._scheduled_scan_to_dict(row)

    def list_scheduled_scans(
        self,
        user_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List scheduled scans with optional status filter."""
        with Session(self.engine) as session:
            stmt = select(ScheduledScanRow).order_by(ScheduledScanRow.created_at.desc())
            if user_id is not None:
                stmt = stmt.where(ScheduledScanRow.user_id == user_id)
            if status is not None:
                stmt = stmt.where(ScheduledScanRow.status == status)
            stmt = stmt.offset(offset).limit(limit)
            rows = session.execute(stmt).scalars().all()
            return [self._scheduled_scan_to_dict(r) for r in rows]

    def count_scheduled_scans(self, user_id: str, status: str | None = None) -> int:
        """Count scheduled scans for a user, optionally by status."""
        with Session(self.engine) as session:
            stmt = select(func.count(ScheduledScanRow.id)).where(
                ScheduledScanRow.user_id == user_id
            )
            if status is not None:
                stmt = stmt.where(ScheduledScanRow.status == status)
            return session.execute(stmt).scalar_one()

    def update_scheduled_scan(self, schedule_id: int, **kwargs) -> None:
        """Update fields on a scheduled scan row."""
        from sqlalchemy import update

        with Session(self.engine) as session:
            stmt = (
                update(ScheduledScanRow).where(ScheduledScanRow.id == schedule_id).values(**kwargs)
            )
            session.execute(stmt)
            session.commit()

    def delete_scheduled_scan(self, schedule_id: int) -> bool:
        """Delete a scheduled scan. Returns True if deleted."""
        with Session(self.engine) as session:
            row = session.execute(
                select(ScheduledScanRow).where(ScheduledScanRow.id == schedule_id)
            ).scalar_one_or_none()
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True

    def get_active_schedules(self) -> list[dict]:
        """Get all schedules with status='active'. Used by scheduler on startup."""
        with Session(self.engine) as session:
            stmt = (
                select(ScheduledScanRow)
                .where(ScheduledScanRow.status == "active")
                .order_by(ScheduledScanRow.id)
            )
            rows = session.execute(stmt).scalars().all()
            return [self._scheduled_scan_to_dict(r) for r in rows]

    # --- Ban engine (collection) methods ---

    def get_banned_collection_cards(
        self,
        user_id: str,
        format_filter: str | None = None,
        statuses: list[str] | None = None,
    ) -> list[dict]:
        """Get collection cards that are banned/restricted, via single JOIN query.

        Only includes cards with card_id IS NOT NULL (linked cards).
        """
        if statuses is None:
            statuses = ["banned", "restricted"]
        with Session(self.engine) as session:
            stmt = (
                select(
                    UserCollectionRow.id.label("entry_id"),
                    UserCollectionRow.card_id,
                    UserCollectionRow.name_en,
                    UserCollectionRow.name_pt,
                    UserCollectionRow.set_code,
                    UserCollectionRow.collector_number,
                    UserCollectionRow.quantity,
                    CardLegalityRow.format,
                    CardLegalityRow.status,
                    CardLegalityRow.effective_date,
                )
                .join(
                    CardLegalityRow,
                    CardLegalityRow.card_id == UserCollectionRow.card_id,
                )
                .where(
                    UserCollectionRow.user_id == user_id,
                    UserCollectionRow.card_id.isnot(None),
                    CardLegalityRow.status.in_(statuses),
                )
            )
            if format_filter:
                stmt = stmt.where(CardLegalityRow.format == format_filter)
            stmt = stmt.order_by(
                CardLegalityRow.status,
                UserCollectionRow.name_en,
                CardLegalityRow.format,
            )
            rows = session.execute(stmt).all()
            return [
                {
                    "entry_id": r.entry_id,
                    "card_id": r.card_id,
                    "name_en": r.name_en,
                    "name_pt": r.name_pt,
                    "set_code": r.set_code,
                    "collector_number": r.collector_number,
                    "quantity": r.quantity,
                    "format": r.format,
                    "status": r.status,
                    "effective_date": r.effective_date,
                }
                for r in rows
            ]

    def get_collection_ban_summary(self, user_id: str) -> dict:
        """Count distinct banned/restricted cards in the user's collection.

        Returns dict: {"banned_count": int, "restricted_count": int}
        """
        with Session(self.engine) as session:
            stmt = (
                select(
                    CardLegalityRow.status,
                    func.count(func.distinct(UserCollectionRow.card_id)),
                )
                .join(
                    CardLegalityRow,
                    CardLegalityRow.card_id == UserCollectionRow.card_id,
                )
                .where(
                    UserCollectionRow.user_id == user_id,
                    UserCollectionRow.card_id.isnot(None),
                    CardLegalityRow.status.in_(["banned", "restricted"]),
                )
                .group_by(CardLegalityRow.status)
            )
            rows = session.execute(stmt).all()
            result = {"banned_count": 0, "restricted_count": 0}
            for status, count in rows:
                if status == "banned":
                    result["banned_count"] = count
                elif status == "restricted":
                    result["restricted_count"] = count
            return result

    def get_card_legalities_with_history(self, card_id: int, days: int = 30) -> list[dict]:
        """Fetch all legalities for a card, enriched with recent change info.

        LEFT JOINs legality_history to detect changes within the last N days.
        """
        cutoff = datetime.now() - timedelta(days=days)
        with Session(self.engine) as session:
            # Subquery: most recent change per (card_id, format)
            recent_change = (
                select(
                    LegalityHistoryRow.format,
                    LegalityHistoryRow.old_status,
                    LegalityHistoryRow.changed_at,
                )
                .where(
                    LegalityHistoryRow.card_id == card_id,
                    LegalityHistoryRow.changed_at >= cutoff,
                )
                .order_by(LegalityHistoryRow.changed_at.desc())
                .subquery()
            )

            stmt = (
                select(
                    CardLegalityRow.format,
                    CardLegalityRow.status,
                    CardLegalityRow.effective_date,
                    recent_change.c.changed_at.label("change_date"),
                    recent_change.c.old_status.label("old_status"),
                )
                .outerjoin(
                    recent_change,
                    CardLegalityRow.format == recent_change.c.format,
                )
                .where(CardLegalityRow.card_id == card_id)
                .order_by(CardLegalityRow.format)
            )
            rows = session.execute(stmt).all()
            return [
                {
                    "format": r.format,
                    "status": r.status,
                    "effective_date": r.effective_date,
                    "recently_changed": r.change_date is not None,
                    "change_date": r.change_date,
                    "old_status": r.old_status,
                }
                for r in rows
            ]

    def get_recently_changed_card_ids(self, user_id: str, days: int = 7) -> set[int]:
        """Find card_ids in the user's collection that had legality changes recently.

        Returns a set for O(1) lookup.
        """
        cutoff = datetime.now() - timedelta(days=days)
        with Session(self.engine) as session:
            stmt = (
                select(func.distinct(UserCollectionRow.card_id))
                .join(
                    LegalityHistoryRow,
                    LegalityHistoryRow.card_id == UserCollectionRow.card_id,
                )
                .where(
                    UserCollectionRow.user_id == user_id,
                    UserCollectionRow.card_id.isnot(None),
                    LegalityHistoryRow.changed_at >= cutoff,
                )
            )
            rows = session.execute(stmt).all()
            return {r[0] for r in rows}

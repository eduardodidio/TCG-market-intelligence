"""Catalog REST API — public endpoints for the offline card catalog."""

from __future__ import annotations

from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.api.schemas.envelope import ApiResponse, success_response
from src.database.repository import Repository

router = APIRouter(prefix="/catalog", tags=["catalog"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CatalogCardItem(BaseModel):
    id: int
    name_en: str
    name_pt: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    rarity: str | None = None
    color_identity: str | None = None
    mana_cost: str | None = None
    type_line: str | None = None
    image_uri: str | None = None
    liga_price: float | None = None
    liga_price_date: str | None = None


class CatalogCardList(BaseModel):
    items: list[CatalogCardItem]
    total: int
    limit: int
    offset: int


class CatalogSetItem(BaseModel):
    set_code: str
    card_count: int
    priced_count: int


class CatalogStats(BaseModel):
    total_cards: int
    total_sets: int
    cards_with_price: int
    cards_without_price: int


class SortByEnum(str, Enum):
    name = "name"
    set_code = "set_code"
    price = "price"


class SortDirEnum(str, Enum):
    asc = "asc"
    desc = "desc"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/cards", response_model=ApiResponse[CatalogCardList])
def list_catalog_cards(
    set_code: str | None = None,
    rarity: str | None = None,
    color: str | None = None,
    name: str | None = None,
    has_price: bool | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort_by: SortByEnum = SortByEnum.name,
    sort_dir: SortDirEnum = SortDirEnum.asc,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repo: Repository = Depends(get_db),
):
    """Paginated card list with filters and optional Liga price."""
    # Build the base query with latest Liga price via window function
    base_sql = """
        SELECT c.id, c.name_en, c.name_pt, c.set_code, c.collector_number,
               c.rarity, c.color_identity, c.mana_cost, c.type_line, c.image_uri,
               po.median_price AS liga_price,
               po.observed_at AS liga_price_date
        FROM cards c
        LEFT JOIN source_cards sc ON sc.card_id = c.id AND sc.source = 'liga'
        LEFT JOIN (
            SELECT external_id, median_price, observed_at,
                   ROW_NUMBER() OVER (
                       PARTITION BY external_id ORDER BY observed_at DESC
                   ) AS rn
            FROM price_observations WHERE source = 'liga'
        ) po ON po.external_id = sc.external_id AND po.rn = 1
        WHERE c.game = 'magic'
    """

    count_sql = """
        SELECT COUNT(*)
        FROM cards c
        LEFT JOIN source_cards sc ON sc.card_id = c.id AND sc.source = 'liga'
        LEFT JOIN (
            SELECT external_id, median_price, observed_at,
                   ROW_NUMBER() OVER (
                       PARTITION BY external_id ORDER BY observed_at DESC
                   ) AS rn
            FROM price_observations WHERE source = 'liga'
        ) po ON po.external_id = sc.external_id AND po.rn = 1
        WHERE c.game = 'magic'
    """

    params: dict = {}
    filters = []

    if set_code is not None:
        filters.append("c.set_code = :set_code")
        params["set_code"] = set_code

    if rarity is not None:
        filters.append("c.rarity = :rarity")
        params["rarity"] = rarity

    if color is not None:
        # Color param may be comma-separated (e.g. "W,U") — each color
        # must be present individually in color_identity (stored as "WU").
        color_letters = [c.strip() for c in color.split(",") if c.strip()]
        for i, letter in enumerate(color_letters):
            key = f"color_{i}"
            filters.append(f"c.color_identity LIKE :{key}")
            params[key] = f"%{letter}%"

    if name is not None:
        filters.append("(c.name_en LIKE :name OR c.name_pt LIKE :name)")
        params["name"] = f"%{name}%"

    if has_price is True:
        filters.append("po.median_price IS NOT NULL")
    elif has_price is False:
        filters.append("po.median_price IS NULL")

    if min_price is not None:
        filters.append("po.median_price >= :min_price")
        params["min_price"] = min_price

    if max_price is not None:
        filters.append("po.median_price <= :max_price")
        params["max_price"] = max_price

    filter_clause = ""
    if filters:
        filter_clause = " AND " + " AND ".join(filters)

    # Sort mapping
    sort_col_map = {
        SortByEnum.name: "c.name_en",
        SortByEnum.set_code: "c.set_code",
        SortByEnum.price: "po.median_price",
    }
    sort_column = sort_col_map[sort_by]
    direction = "ASC" if sort_dir == SortDirEnum.asc else "DESC"

    # For price sort with nulls, push nulls to end
    if sort_by == SortByEnum.price:
        null_sort = "CASE WHEN po.median_price IS NULL THEN 1 ELSE 0 END"
        order_clause = f" ORDER BY {null_sort}, {sort_column} {direction}"
    else:
        order_clause = f" ORDER BY {sort_column} {direction}"

    # Add deterministic tiebreaker
    order_clause += ", c.id ASC"

    full_query = base_sql + filter_clause + order_clause + " LIMIT :limit OFFSET :offset"
    full_count = count_sql + filter_clause

    params["limit"] = limit
    params["offset"] = offset

    with Session(repo.engine) as session:
        rows = session.execute(text(full_query), params).fetchall()
        total = session.execute(text(full_count), params).scalar() or 0

    items = []
    for row in rows:
        liga_price = float(row.liga_price) if row.liga_price is not None else None
        liga_price_date = str(row.liga_price_date) if row.liga_price_date is not None else None
        items.append(
            CatalogCardItem(
                id=row.id,
                name_en=row.name_en,
                name_pt=row.name_pt,
                set_code=row.set_code,
                collector_number=row.collector_number,
                rarity=row.rarity,
                color_identity=row.color_identity,
                mana_cost=row.mana_cost,
                type_line=row.type_line,
                image_uri=row.image_uri,
                liga_price=liga_price,
                liga_price_date=liga_price_date,
            )
        )

    data = CatalogCardList(items=items, total=total, limit=limit, offset=offset)
    return success_response(data=data)


@router.get("/cards/{card_id}", response_model=ApiResponse[CatalogCardItem])
def get_catalog_card(
    card_id: int,
    repo: Repository = Depends(get_db),
):
    """Single card details with Liga price."""
    query = """
        SELECT c.id, c.name_en, c.name_pt, c.set_code, c.collector_number,
               c.rarity, c.color_identity, c.mana_cost, c.type_line, c.image_uri,
               po.median_price AS liga_price,
               po.observed_at AS liga_price_date
        FROM cards c
        LEFT JOIN source_cards sc ON sc.card_id = c.id AND sc.source = 'liga'
        LEFT JOIN (
            SELECT external_id, median_price, observed_at,
                   ROW_NUMBER() OVER (
                       PARTITION BY external_id ORDER BY observed_at DESC
                   ) AS rn
            FROM price_observations WHERE source = 'liga'
        ) po ON po.external_id = sc.external_id AND po.rn = 1
        WHERE c.game = 'magic' AND c.id = :card_id
    """

    with Session(repo.engine) as session:
        row = session.execute(text(query), {"card_id": card_id}).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Card not found")

    liga_price = float(row.liga_price) if row.liga_price is not None else None
    liga_price_date = str(row.liga_price_date) if row.liga_price_date is not None else None

    data = CatalogCardItem(
        id=row.id,
        name_en=row.name_en,
        name_pt=row.name_pt,
        set_code=row.set_code,
        collector_number=row.collector_number,
        rarity=row.rarity,
        color_identity=row.color_identity,
        mana_cost=row.mana_cost,
        type_line=row.type_line,
        image_uri=row.image_uri,
        liga_price=liga_price,
        liga_price_date=liga_price_date,
    )
    return success_response(data=data)


@router.get("/sets", response_model=ApiResponse[list[CatalogSetItem]])
def list_catalog_sets(
    repo: Repository = Depends(get_db),
):
    """List of sets in the catalog with card and priced counts."""
    query = """
        SELECT c.set_code,
               COUNT(*) AS card_count,
               COUNT(po.median_price) AS priced_count
        FROM cards c
        LEFT JOIN source_cards sc ON sc.card_id = c.id AND sc.source = 'liga'
        LEFT JOIN (
            SELECT external_id, median_price,
                   ROW_NUMBER() OVER (
                       PARTITION BY external_id ORDER BY observed_at DESC
                   ) AS rn
            FROM price_observations WHERE source = 'liga'
        ) po ON po.external_id = sc.external_id AND po.rn = 1
        WHERE c.game = 'magic' AND c.set_code IS NOT NULL
        GROUP BY c.set_code
        ORDER BY c.set_code ASC
    """

    with Session(repo.engine) as session:
        rows = session.execute(text(query)).fetchall()

    data = [
        CatalogSetItem(
            set_code=row.set_code,
            card_count=row.card_count,
            priced_count=row.priced_count,
        )
        for row in rows
    ]
    return success_response(data=data)


@router.get("/stats", response_model=ApiResponse[CatalogStats])
def get_catalog_stats(
    repo: Repository = Depends(get_db),
):
    """Catalog statistics: totals for cards, sets, priced/unpriced."""
    query = """
        SELECT
            COUNT(*) AS total_cards,
            COUNT(DISTINCT c.set_code) AS total_sets,
            COUNT(po.median_price) AS cards_with_price
        FROM cards c
        LEFT JOIN source_cards sc ON sc.card_id = c.id AND sc.source = 'liga'
        LEFT JOIN (
            SELECT external_id, median_price,
                   ROW_NUMBER() OVER (
                       PARTITION BY external_id ORDER BY observed_at DESC
                   ) AS rn
            FROM price_observations WHERE source = 'liga'
        ) po ON po.external_id = sc.external_id AND po.rn = 1
        WHERE c.game = 'magic'
    """

    with Session(repo.engine) as session:
        row = session.execute(text(query)).fetchone()

    total_cards = row.total_cards if row else 0
    total_sets = row.total_sets if row else 0
    cards_with_price = row.cards_with_price if row else 0

    data = CatalogStats(
        total_cards=total_cards,
        total_sets=total_sets,
        cards_with_price=cards_with_price,
        cards_without_price=total_cards - cards_with_price,
    )
    return success_response(data=data)

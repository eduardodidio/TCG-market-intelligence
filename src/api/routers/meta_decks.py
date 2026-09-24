"""Metagame top decks API router (F173)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_optional_user
from src.api.error_codes import ErrorCode, api_error
from src.api.schemas.envelope import ApiResponse, success_response
from src.database.models import CardRow
from src.database.repository import Repository
from src.domain.models import User
from src.metagame.models import MetaDeckCardRow, MetaDeckRow
from src.metagame.repository import MetagameRepository
from src.metagame.valuation import BASIC_LANDS, value_meta_deck

router = APIRouter(prefix="/meta-decks", tags=["meta-decks"])

MetaFormat = Literal["commander", "standard", "pioneer", "modern", "legacy", "pauper", "vintage"]


# --- Schemas ---


class MetaFormatInfo(BaseModel):
    format: str
    latest_snapshot_date: date | None = None
    deck_count: int


class MetaFormatsResponse(BaseModel):
    formats: list[MetaFormatInfo]


class MetaDeckSummary(BaseModel):
    id: int
    rank: int
    archetype: str
    commander_name: str | None = None
    colors: str | None = None
    meta_share_pct: float | None = None
    deck_count: int | None = None
    source: str
    source_url: str
    event_date: date | None = None
    snapshot_date: date
    total_value_brl: float | None = None
    priced_pct: float | None = None
    owned_pct: float | None = None
    missing_value_brl: float | None = None
    total_copies: int


class MetaDeckListResponse(BaseModel):
    format: str
    snapshot_date: date | None = None
    source: str | None = None
    total: int
    decks: list[MetaDeckSummary]


class MetaDeckCard(BaseModel):
    name: str
    quantity: int
    board: str
    card_id: int | None = None
    price_brl: float | None = None
    owned_qty: int | None = None
    image_url: str | None = None


class MetaDeckDetail(MetaDeckSummary):
    cards: list[MetaDeckCard]


# --- Dependencies / helpers ---


def get_meta_repo(repo: Repository = Depends(get_db)) -> MetagameRepository:
    return MetagameRepository.from_repo(repo)


def _to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _card_ids(cards_by_deck: dict[int, list[MetaDeckCardRow]]) -> list[int]:
    return sorted(
        {c.card_id for cards in cards_by_deck.values() for c in cards if c.card_id is not None}
    )


def _latest_prices(repo: Repository, card_ids: list[int]) -> dict[int, Decimal | None]:
    """Latest BRL price per card (same source as ``/decks/ranking``)."""
    raw = repo.get_latest_prices_batch(card_ids) if card_ids else {}
    prices: dict[int, Decimal | None] = {}
    for cid, obs in raw.items():
        if obs is not None and obs.median_price is not None:
            prices[cid] = Decimal(str(obs.median_price))
        else:
            prices[cid] = None
    return prices


def _owned(
    meta: MetagameRepository, user: User | None, card_ids: list[int]
) -> dict[int, int] | None:
    if user is None:
        return None
    return meta.owned_quantities(str(user.id), card_ids)


def _summary(
    deck: MetaDeckRow,
    cards: list[MetaDeckCardRow],
    prices: dict[int, Decimal | None],
    owned: dict[int, int] | None,
) -> dict:
    valuation = value_meta_deck(cards, prices, owned)
    return {
        "id": deck.id,
        "rank": deck.rank,
        "archetype": deck.archetype,
        "commander_name": deck.commander_name,
        "colors": deck.colors,
        "meta_share_pct": _to_float(deck.meta_share_pct),
        "deck_count": deck.deck_count,
        "source": deck.source,
        "source_url": deck.source_url,
        "event_date": deck.event_date,
        "snapshot_date": deck.snapshot_date,
        "total_value_brl": _to_float(valuation.total_value_brl),
        "priced_pct": _to_float(valuation.priced_pct),
        "owned_pct": _to_float(valuation.owned_pct),
        "missing_value_brl": _to_float(valuation.missing_value_brl),
        "total_copies": valuation.total_copies,
    }


def _image_urls(repo: Repository, card_ids: list[int]) -> dict[int, str | None]:
    if not card_ids:
        return {}
    with Session(repo.engine) as session:
        rows = session.execute(
            select(CardRow.id, CardRow.image_uri).where(CardRow.id.in_(card_ids))
        ).all()
    return {cid: uri for cid, uri in rows}


# --- Endpoints ---


@router.get("/formats", response_model=ApiResponse[MetaFormatsResponse])
def list_meta_formats(meta: MetagameRepository = Depends(get_meta_repo)):
    """Formats with a collected snapshot: latest snapshot date and its deck count."""
    formats = [MetaFormatInfo(**row) for row in meta.list_formats()]
    return success_response(MetaFormatsResponse(formats=formats))


@router.get("", response_model=ApiResponse[MetaDeckListResponse])
def list_meta_decks(
    format: MetaFormat = Query(...),
    snapshot_date: date | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    repo: Repository = Depends(get_db),
    meta: MetagameRepository = Depends(get_meta_repo),
    user: User | None = Depends(get_optional_user),
):
    """Metagame decks of one format (latest snapshot by default), valued in BRL."""
    snap = snapshot_date or meta.latest_snapshot_date(format)
    if snap is None:
        return success_response(
            MetaDeckListResponse(format=format, snapshot_date=None, source=None, total=0, decks=[])
        )

    decks, total = meta.list_decks(format, snapshot_date=snap, limit=limit, offset=offset)
    cards_by_deck = meta.get_deck_cards([d.id for d in decks])
    card_ids = _card_ids(cards_by_deck)
    prices = _latest_prices(repo, card_ids)
    owned = _owned(meta, user, card_ids)

    summaries = [
        MetaDeckSummary(**_summary(d, cards_by_deck.get(d.id, []), prices, owned)) for d in decks
    ]
    return success_response(
        MetaDeckListResponse(
            format=format,
            snapshot_date=snap if total else None,
            source=decks[0].source if decks else None,
            total=total,
            decks=summaries,
        )
    )


@router.get("/{deck_id}", response_model=ApiResponse[MetaDeckDetail])
def get_meta_deck(
    deck_id: int,
    repo: Repository = Depends(get_db),
    meta: MetagameRepository = Depends(get_meta_repo),
    user: User | None = Depends(get_optional_user),
):
    """One metagame deck with its decklist, per-card BRL price and owned quantity."""
    deck = meta.get_deck(deck_id)
    if deck is None:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, f"Meta deck {deck_id} not found")

    cards_by_deck = meta.get_deck_cards([deck.id])
    cards = cards_by_deck.get(deck.id, [])
    card_ids = _card_ids(cards_by_deck)
    prices = _latest_prices(repo, card_ids)
    owned = _owned(meta, user, card_ids)
    images = _image_urls(repo, card_ids)

    card_items: list[MetaDeckCard] = []
    for c in cards:
        if owned is None:
            owned_qty = None
        elif c.card_name.strip() in BASIC_LANDS:
            owned_qty = c.quantity
        else:
            owned_qty = owned.get(c.card_id, 0) if c.card_id is not None else 0
        card_items.append(
            MetaDeckCard(
                name=c.card_name,
                quantity=c.quantity,
                board=c.board,
                card_id=c.card_id,
                price_brl=_to_float(prices.get(c.card_id)) if c.card_id is not None else None,
                owned_qty=owned_qty,
                image_url=images.get(c.card_id) if c.card_id is not None else None,
            )
        )

    return success_response(
        MetaDeckDetail(**_summary(deck, cards, prices, owned), cards=card_items)
    )

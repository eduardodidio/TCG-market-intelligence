"""Deck management API endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.schemas.decks import (
    DeckCardSchema,
    DeckDetailSchema,
    DeckImportRequest,
    DeckImportResult,
    DeckSummarySchema,
)
from src.api.schemas.envelope import ApiResponse, success_response
from src.database.repository import Repository
from src.services.currency import CurrencyConverter
from src.utils.set_code_map import map_to_scryfall_set_code

router = APIRouter(prefix="/decks", tags=["decks"])


def _scryfall_image_url(set_code: str, collector_number: str) -> str:
    mapped = map_to_scryfall_set_code(set_code)
    return (
        f"https://api.scryfall.com/cards/{mapped}/{collector_number}"
        f"?format=image&version=normal"
    )


@router.post("", response_model=ApiResponse[DeckImportResult])
def import_deck(
    request: DeckImportRequest,
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Import a deck from text or CSV content."""
    from src.decks.importer import import_deck_from_csv, import_deck_from_text

    if request.format == "csv":
        result = import_deck_from_csv(
            engine=repo.engine,
            user_id=user_id,
            name=request.name,
            csv_content=request.content,
            description=request.description,
        )
    else:
        result = import_deck_from_text(
            engine=repo.engine,
            user_id=user_id,
            name=request.name,
            content=request.content,
            description=request.description,
        )

    return success_response(data=DeckImportResult(**result))


@router.get("", response_model=ApiResponse[list[DeckSummarySchema]])
def list_decks(
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """List all decks for the authenticated user."""
    decks = repo.list_decks(user_id)
    data = []
    for deck in decks:
        summary = repo.get_deck_summary(deck.id, user_id)
        data.append(
            DeckSummarySchema(
                id=deck.id,
                name=deck.name,
                description=deck.description,
                total_cards=summary["total_cards"],
                unique_cards=summary["unique_cards"],
                owned_cards=summary["owned_cards"],
                ownership_pct=summary["ownership_pct"],
                created_at=deck.created_at,
                updated_at=deck.updated_at,
            )
        )
    return success_response(data=data)


@router.get("/{deck_id}", response_model=ApiResponse[DeckDetailSchema])
def get_deck(
    deck_id: int,
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Get a deck with full detail including ownership and prices."""
    deck = repo.get_deck(deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != user_id:
        raise HTTPException(status_code=404, detail="Deck not found")

    cards_with_ownership = repo.get_deck_cards_with_ownership(deck_id, user_id)
    summary = repo.get_deck_summary(deck_id, user_id)

    # Batch-fetch latest prices for linked cards
    linked_card_ids = [c["card_id"] for c in cards_with_ownership if c["card_id"] is not None]
    latest_prices = repo.get_latest_prices_batch(linked_card_ids) if linked_card_ids else {}

    card_schemas = []
    for c in cards_with_ownership:
        image_url = None
        if c["set_code"] and c["collector_number"]:
            image_url = _scryfall_image_url(c["set_code"], c["collector_number"])

        latest_price = None
        if c["card_id"] is not None:
            obs = latest_prices.get(c["card_id"])
            if obs and obs.median_price:
                latest_price = float(converter.convert(obs.median_price, date.today(), "BRL") or 0)

        card_schemas.append(
            DeckCardSchema(
                id=c["id"],
                name_en=c["name_en"],
                set_code=c["set_code"],
                collector_number=c["collector_number"],
                quantity=c["quantity"],
                card_id=c["card_id"],
                in_collection=c["in_collection"],
                owned_quantity=c["owned_quantity"],
                collection_entry_id=c["collection_entry_id"],
                image_url=image_url,
                latest_price=latest_price,
            )
        )

    detail = DeckDetailSchema(
        id=deck.id,
        name=deck.name,
        description=deck.description,
        cards=card_schemas,
        total_cards=summary["total_cards"],
        unique_cards=summary["unique_cards"],
        owned_cards=summary["owned_cards"],
        ownership_pct=summary["ownership_pct"],
        created_at=deck.created_at,
        updated_at=deck.updated_at,
    )

    return success_response(data=detail)


@router.delete("/{deck_id}", status_code=204)
def delete_deck(
    deck_id: int,
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Delete a deck."""
    deleted = repo.delete_deck(deck_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Deck not found")
    return Response(status_code=204)

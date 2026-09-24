"""Deck suggestion request endpoints (F172).

Requests are only registered here; a daily local routine asks Claude to
build the deck (see ``src/deck_suggestions``). The result can then be saved
as a regular deck.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response

from src.api.deps import get_db, require_auth_or_api_key
from src.api.error_codes import ErrorCode, api_error
from src.api.schemas.deck_suggestions import (
    SUGGESTION_ARCHETYPES,
    SUGGESTION_FORMATS,
    SUGGESTION_STATUSES,
    DeckSuggestionCreate,
    DeckSuggestionSave,
    DeckSuggestionSavedResponse,
    DeckSuggestionSchema,
    to_schema,
)
from src.api.schemas.envelope import ApiResponse, success_response
from src.database.repository import Repository
from src.deck_suggestions import repository as sugg_repo
from src.decks.builder import is_commander_eligible

router = APIRouter(prefix="/deck-suggestions", tags=["decks"])

MAX_OPEN_REQUESTS = 5
_WUBRG = set("WUBRG")


def _commander_colors(color_identity: str | None) -> str:
    colors = [c for c in (color_identity or "") if c in _WUBRG]
    return sugg_repo.colors_to_str(colors) or "C"


def _validate_create(body: DeckSuggestionCreate, repo: Repository) -> dict:
    """Validate a create request and return kwargs for ``create_request``."""
    fmt = (body.format_name or "").strip().lower()
    if fmt not in SUGGESTION_FORMATS:
        raise api_error(
            400,
            ErrorCode.VALIDATION_ERROR,
            f"Unknown format: {body.format_name}. "
            f"Valid formats: {', '.join(sorted(SUGGESTION_FORMATS))}",
            field="format_name",
        )

    archetype = (body.archetype or "").strip().lower() or None
    if archetype is not None and archetype not in SUGGESTION_ARCHETYPES:
        raise api_error(
            400,
            ErrorCode.VALIDATION_ERROR,
            f"Unknown archetype: {body.archetype}. "
            f"Valid archetypes: {', '.join(sorted(SUGGESTION_ARCHETYPES))}",
            field="archetype",
        )

    notes = (body.notes or "").strip() or None

    if fmt == "commander":
        if body.commander_card_id is None:
            raise api_error(
                400,
                ErrorCode.VALIDATION_ERROR,
                "commander_card_id is required for the commander format",
                field="commander_card_id",
            )
        card = repo.get_card_by_id(body.commander_card_id)
        if card is None:
            raise api_error(
                400,
                ErrorCode.VALIDATION_ERROR,
                "Commander card not found in catalog",
                field="commander_card_id",
            )
        if not is_commander_eligible(card.type_line):
            raise api_error(
                400,
                ErrorCode.VALIDATION_ERROR,
                f"Card '{card.name_en}' is not a Legendary Creature",
                field="commander_card_id",
            )
        return {
            "format_name": fmt,
            "commander_card_id": card.id,
            "commander_name": card.name_en,
            "colors": _commander_colors(card.color_identity),
            "archetype": archetype,
            "notes": notes,
        }

    letters = {c.strip().upper() for c in body.colors if c and c.strip()}
    if not letters or not (letters <= _WUBRG or letters == {"C"}):
        raise api_error(
            400,
            ErrorCode.VALIDATION_ERROR,
            "colors must be a non-empty subset of W, U, B, R, G, or exactly ['C']",
            field="colors",
        )
    if archetype is None:
        raise api_error(
            400,
            ErrorCode.VALIDATION_ERROR,
            f"archetype is required for the {fmt} format",
            field="archetype",
        )
    return {
        "format_name": fmt,
        "commander_card_id": None,
        "commander_name": None,
        "colors": sugg_repo.colors_to_str(sorted(letters)),
        "archetype": archetype,
        "notes": notes,
    }


def _get_owned(repo: Repository, request_id: int, user_id: str):
    row = sugg_repo.get_request(repo.engine, request_id, user_id)
    if row is None:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Deck suggestion not found")
    return row


def _cards_for_deck(result: dict) -> list[dict]:
    """Map the suggestion result into ``add_deck_cards`` dicts (commander first)."""
    cards: list[dict] = []
    seen_names: set[str] = set()
    commander = result.get("commander")
    if isinstance(commander, dict) and commander.get("name_en"):
        cards.append(
            {
                "name_en": commander["name_en"],
                "set_code": commander.get("set_code"),
                "collector_number": commander.get("collector_number"),
                "quantity": 1,
                "card_id": commander.get("card_id"),
            }
        )
        seen_names.add(commander["name_en"].lower())
    for c in result.get("cards") or []:
        if not isinstance(c, dict) or not c.get("name_en"):
            continue
        if c["name_en"].lower() in seen_names:
            continue
        try:
            quantity = max(1, int(c.get("quantity") or 1))
        except (TypeError, ValueError):
            quantity = 1
        cards.append(
            {
                "name_en": c["name_en"],
                "set_code": c.get("set_code"),
                "collector_number": c.get("collector_number"),
                "quantity": quantity,
                "card_id": c.get("card_id"),
            }
        )
    return cards


@router.post("", status_code=201, response_model=ApiResponse[DeckSuggestionSchema])
def create_suggestion(
    body: DeckSuggestionCreate,
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Register a deck suggestion request (processed later by a daily routine)."""
    fields = _validate_create(body, repo)
    if sugg_repo.count_open_requests(repo.engine, user_id) >= MAX_OPEN_REQUESTS:
        raise api_error(
            429,
            ErrorCode.VALIDATION_LIMIT_EXCEEDED,
            f"You already have {MAX_OPEN_REQUESTS} open suggestion requests. "
            "Wait for them to be processed.",
        )
    row = sugg_repo.create_request(repo.engine, user_id=user_id, **fields)
    return success_response(data=to_schema(row, include_result=False))


@router.get("", response_model=ApiResponse[list[DeckSuggestionSchema]])
def list_suggestions(
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """List the user's suggestion requests, newest first."""
    if status is not None and status not in SUGGESTION_STATUSES:
        raise api_error(
            400,
            ErrorCode.VALIDATION_ERROR,
            f"Invalid status: {status}. Valid statuses: {', '.join(SUGGESTION_STATUSES)}",
            field="status",
        )
    rows = sugg_repo.list_requests(repo.engine, user_id, status=status, limit=limit)
    return success_response(data=[to_schema(r, include_result=False) for r in rows])


@router.get("/{request_id}", response_model=ApiResponse[DeckSuggestionSchema])
def get_suggestion(
    request_id: int,
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Get one suggestion request, including its full result when done."""
    row = _get_owned(repo, request_id, user_id)
    return success_response(data=to_schema(row, include_result=True))


@router.post("/{request_id}/save", response_model=ApiResponse[DeckSuggestionSavedResponse])
def save_suggestion_as_deck(
    request_id: int,
    body: DeckSuggestionSave | None = None,
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Save a finished suggestion as a deck (idempotent)."""
    row = _get_owned(repo, request_id, user_id)
    if row.status != "done":
        raise api_error(
            409,
            ErrorCode.RESOURCE_CONFLICT,
            f"Suggestion is not ready to be saved (status: {row.status})",
        )
    if row.saved_deck_id is not None and repo.get_deck(row.saved_deck_id) is not None:
        return success_response(data=DeckSuggestionSavedResponse(deck_id=row.saved_deck_id))

    result = sugg_repo.load_result(row)
    if result is None:
        raise api_error(409, ErrorCode.RESOURCE_CONFLICT, "Suggestion result is unavailable")

    name = (body.deck_name if body else None) or result.get("deck_name")
    name = (str(name).strip() if name else "") or f"Deck suggestion #{row.id}"
    deck = repo.create_deck(user_id, name[:300])
    repo.add_deck_cards(deck.id, _cards_for_deck(result))
    sugg_repo.set_saved_deck(repo.engine, row.id, deck.id)
    return success_response(data=DeckSuggestionSavedResponse(deck_id=deck.id))


@router.delete("/{request_id}", status_code=204)
def delete_suggestion(
    request_id: int,
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Delete a suggestion request while it is still pending."""
    row = _get_owned(repo, request_id, user_id)
    if row.status != "pending" or not sugg_repo.delete_pending_request(
        repo.engine, request_id, user_id
    ):
        raise api_error(
            409,
            ErrorCode.RESOURCE_CONFLICT,
            f"Only pending suggestions can be deleted (status: {row.status})",
        )
    return Response(status_code=204)

"""Web card search router — search LigaMagic for cards not in local DB."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from urllib.parse import quote_plus

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.api.deps import get_credit_service, get_current_user, get_db
from src.api.schemas.card_search import WebSearchResult
from src.api.schemas.envelope import ApiResponse, success_response
from src.credits.exceptions import InsufficientCreditsError
from src.credits.service import CreditService
from src.database.repository import Repository
from src.domain.models import User

log = structlog.get_logger()

router = APIRouter(tags=["cards"])

_SEARCH_TIMEOUT_SECONDS = 30


def _find_local_card(repo: Repository, card_name: str) -> int | None:
    """Case-insensitive search for a card in the local DB by name."""
    cards = repo.list_cards(name_search=card_name, limit=1)
    if cards and cards[0].name_en.lower() == card_name.lower():
        return cards[0].id
    return None


def _decimal_to_float(val: Decimal | None) -> float | None:
    if val is None:
        return None
    return float(val)


@router.get("/cards/search-web", response_model=ApiResponse[list[WebSearchResult]])
async def search_web(
    request: Request,
    q: str = Query(..., min_length=1, description="Card name to search"),
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
    credit_svc: CreditService = Depends(get_credit_service),
):
    """Search for cards on LigaMagic.

    Costs 1 credit token per search. Returns price data and optionally
    links to local cards if they exist in the DB.

    Returns 503 if the Liga provider is not available (e.g. Playwright
    not installed or disabled on this deployment).
    """
    # 1. Deduct token
    try:
        credit_svc.deduct(user.id, 1, "web_search", reference_id=q[:100])
    except InsufficientCreditsError:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    # 2. Get Liga provider from registry
    registry = getattr(request.app.state, "provider_registry", None)
    liga_provider = None
    if registry:
        from src.providers.liga.provider import LigaMagicProvider

        for provider in registry.providers:
            if isinstance(provider, LigaMagicProvider):
                liga_provider = provider
                break

    if liga_provider is None:
        raise HTTPException(
            status_code=503,
            detail="Liga search is unavailable on this deployment",
        )

    # 3. Call Liga search with timeout
    try:
        prices = await asyncio.wait_for(
            liga_provider.search_card(q.strip()),
            timeout=_SEARCH_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        log.warning("web_search_timeout", query=q)
        raise HTTPException(status_code=504, detail="Liga search timed out")
    except Exception as e:
        log.warning("web_search_error", query=q, error=str(e))
        raise HTTPException(status_code=502, detail="Liga search failed")

    # 4. Build results
    normal = prices.get("normal", {})
    foil = prices.get("foil", {})
    has_normal = any(v is not None for v in normal.values())
    has_foil = any(v is not None for v in foil.values())

    if not has_normal and not has_foil:
        return success_response(data=[])

    card_name = prices.get("card_name", q.strip())
    local_card_id = _find_local_card(repo, card_name)

    # Build Liga URL for the card
    encoded_name = quote_plus(card_name)
    liga_url = f"https://www.ligamagic.com.br/?view=cards/card&card={encoded_name}"

    normal_price = _decimal_to_float(normal.get("low") or normal.get("mid") or normal.get("high"))
    foil_price = _decimal_to_float(foil.get("low") or foil.get("mid") or foil.get("high"))

    result = WebSearchResult(
        card_name=card_name,
        liga_url=liga_url,
        normal_price=normal_price,
        foil_price=foil_price,
        local_card_id=local_card_id,
    )

    return success_response(data=[result])

"""Web card search router — search LigaMagic (or MYP fallback) for cards not in local DB."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from urllib.parse import quote_plus

import structlog
from fastapi import APIRouter, Depends, Query, Request

from src.api.deps import get_credit_service, get_current_user, get_db
from src.api.error_codes import ErrorCode, api_error
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


def _find_alternate_name(repo: Repository, query: str) -> str | None:
    """Look up the alternate-language name for a card in the local catalog.

    If *query* matches name_pt, return name_en (and vice-versa).
    Returns ``None`` when no match is found.
    """
    from sqlalchemy import func, select
    from sqlalchemy.orm import Session

    from src.database.models import CardRow

    q_lower = query.strip().lower()
    try:
        with Session(repo.engine) as session:
            row = session.execute(
                select(CardRow.name_en, CardRow.name_pt)
                .where(
                    (func.lower(CardRow.name_pt) == q_lower)
                    | (func.lower(CardRow.name_en) == q_lower)
                )
                .limit(1)
            ).first()
    except Exception:
        return None

    if row is None:
        return None

    try:
        name_en, name_pt = row
    except (ValueError, TypeError):
        return None
    # If the query matched the PT name, return EN; otherwise return PT
    if name_pt and name_pt.lower() == q_lower:
        return name_en
    if name_en and name_en.lower() == q_lower:
        return name_pt
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
        raise api_error(402, ErrorCode.CREDIT_INSUFFICIENT, "Insufficient credits")

    # 2. Get search provider from registry (Liga preferred, MYP fallback)
    registry = getattr(request.app.state, "provider_registry", None)
    liga_provider = None
    myp_provider = None
    if registry:
        from src.providers.liga.provider import LigaMagicProvider
        from src.providers.myp.provider import MypCardsProvider

        for provider in registry.providers:
            if isinstance(provider, LigaMagicProvider) and liga_provider is None:
                liga_provider = provider
            elif isinstance(provider, MypCardsProvider) and myp_provider is None:
                myp_provider = provider

    # Liga available — use it (original path)
    if liga_provider is not None:
        return await _search_via_liga(liga_provider, q, repo)

    # MYP fallback
    if myp_provider is not None:
        log.info("web_search_myp_fallback", query=q)
        return await _search_via_myp(myp_provider, q, repo)

    # Neither provider available
    raise api_error(
        503,
        ErrorCode.EXTERNAL_PROVIDER_UNAVAILABLE,
        "Card search is unavailable on this deployment",
    )


async def _search_via_liga(
    liga_provider,
    q: str,
    repo: Repository,
) -> ApiResponse[list[WebSearchResult]]:
    """Execute search via LigaMagic provider."""
    try:
        prices = await asyncio.wait_for(
            liga_provider.search_card(q.strip()),
            timeout=_SEARCH_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        log.warning("web_search_timeout", query=q)
        raise api_error(504, ErrorCode.EXTERNAL_TIMEOUT, "Liga search timed out")
    except Exception as e:
        log.warning("web_search_error", query=q, error=str(e))
        raise api_error(502, ErrorCode.EXTERNAL_FAILURE, "Liga search failed")

    normal = prices.get("normal", {})
    foil = prices.get("foil", {})
    has_normal = any(v is not None for v in normal.values())
    has_foil = any(v is not None for v in foil.values())

    if not has_normal and not has_foil:
        # Retry with alternate-language name from local catalog
        alt_name = _find_alternate_name(repo, q)
        if alt_name:
            log.info("web_search_liga_lang_fallback", original=q, alternate=alt_name)
            try:
                prices = await asyncio.wait_for(
                    liga_provider.search_card(alt_name.strip()),
                    timeout=_SEARCH_TIMEOUT_SECONDS,
                )
            except (asyncio.TimeoutError, Exception):
                # If retry also fails, return empty — don't raise
                return success_response(data=[])
            normal = prices.get("normal", {})
            foil = prices.get("foil", {})
            has_normal = any(v is not None for v in normal.values())
            has_foil = any(v is not None for v in foil.values())
            if not has_normal and not has_foil:
                return success_response(data=[])
        else:
            return success_response(data=[])

    card_name = prices.get("card_name", q.strip())
    local_card_id = _find_local_card(repo, card_name)

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


async def _search_via_myp(
    myp_provider,
    q: str,
    repo: Repository,
) -> ApiResponse[list[WebSearchResult]]:
    """Execute search via MYP provider (fallback when Liga is unavailable)."""
    try:
        myp_results = await asyncio.wait_for(
            myp_provider.search_card(q.strip()),
            timeout=_SEARCH_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        log.warning("web_search_myp_timeout", query=q)
        raise api_error(504, ErrorCode.EXTERNAL_TIMEOUT, "MYP search timed out")
    except Exception as e:
        log.warning("web_search_myp_error", query=q, error=str(e))
        raise api_error(502, ErrorCode.EXTERNAL_FAILURE, "MYP search failed")

    if not myp_results:
        # Retry with alternate-language name from local catalog
        alt_name = _find_alternate_name(repo, q)
        if alt_name:
            log.info("web_search_myp_lang_fallback", original=q, alternate=alt_name)
            try:
                myp_results = await asyncio.wait_for(
                    myp_provider.search_card(alt_name.strip()),
                    timeout=_SEARCH_TIMEOUT_SECONDS,
                )
            except (asyncio.TimeoutError, Exception):
                return success_response(data=[])
        if not myp_results:
            return success_response(data=[])

    results: list[WebSearchResult] = []
    for item in myp_results:
        local_card_id = _find_local_card(repo, item.name)
        results.append(
            WebSearchResult(
                card_name=item.name,
                liga_url=None,
                normal_price=None,
                foil_price=None,
                image_url=item.image_url,
                local_card_id=local_card_id,
            )
        )

    return success_response(data=results)

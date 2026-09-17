"""Deck management API endpoints."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.error_codes import ErrorCode, api_error
from src.api.schemas.deck_ranking import (
    DeckRankingEntry,
    DeckRankingResponse,
    DeckValueDetailSchema,
    DeckValuePointSchema,
)
from src.api.schemas.decks import (
    BudgetAnalysis,
    BudgetEntry,
    ColorDistEntry,
    CommanderCandidate,
    DeckCardSchema,
    DeckDetailSchema,
    DeckEvaluationResponse,
    DeckGenerateRequest,
    DeckGenerateResponse,
    DeckImportRequest,
    DeckImportResult,
    DeckSummarySchema,
    GeneratedCardSchema,
    IllegalCard,
    LegalityResult,
    ManaCurvePoint,
    TypeDistEntry,
)
from src.api.schemas.envelope import ApiResponse, success_response
from src.database.repository import Repository
from src.decks.valuation import (
    compute_deck_value,
    compute_deck_value_change,
    compute_deck_value_series,
)
from src.services.currency import CurrencyConverter
from src.utils.set_code_map import map_to_scryfall_set_code

router = APIRouter(prefix="/decks", tags=["decks"])

_PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90}


def _scryfall_image_url(set_code: str, collector_number: str) -> str:
    mapped = map_to_scryfall_set_code(set_code)
    return f"https://api.scryfall.com/cards/{mapped}/{collector_number}?format=image&version=normal"


def _convert_value(
    value: Decimal | None,
    converter: CurrencyConverter,
    currency: str,
) -> float | None:
    """Convert a Decimal value to float with currency conversion."""
    if value is None:
        return None
    converted = converter.convert(value, date.today(), currency)
    return float(converted) if converted is not None else float(value)


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


@router.get("/ranking", response_model=ApiResponse[DeckRankingResponse])
def get_deck_ranking(
    sort_by: Literal[
        "total_value", "value_change_pct", "value_change_abs", "card_count"
    ] = "total_value",
    sort_order: Literal["desc", "asc"] = "desc",
    period: Literal["7d", "30d", "90d"] = "30d",
    min_value: float | None = None,
    max_value: float | None = None,
    currency: str = "BRL",
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Rank user decks by total value with change indicators and sparklines."""
    decks = repo.list_decks(user_id)
    if not decks:
        return success_response(
            data=DeckRankingResponse(decks=[], total=0, sort_by=sort_by, period=period)
        )

    period_days = _PERIOD_DAYS.get(period, 30)

    # Collect all unique card_ids across all decks
    all_deck_cards: dict[int, list] = {}
    all_card_ids: set[int] = set()

    for deck in decks:
        deck_cards = repo.get_deck_cards(deck.id)
        all_deck_cards[deck.id] = deck_cards
        for dc in deck_cards:
            if dc.card_id is not None:
                all_card_ids.add(dc.card_id)

    # Batch-fetch latest prices and price series
    latest_prices_raw = repo.get_latest_prices_batch(list(all_card_ids)) if all_card_ids else {}
    latest_prices: dict[int, Decimal | None] = {}
    for cid, obs in latest_prices_raw.items():
        if obs and obs.median_price is not None:
            latest_prices[cid] = Decimal(str(obs.median_price))
        else:
            latest_prices[cid] = None

    price_series = (
        repo.get_price_series_batch(list(all_card_ids), days=period_days) if all_card_ids else {}
    )

    # Build ranking entries
    entries: list[DeckRankingEntry] = []

    for deck in decks:
        deck_cards = all_deck_cards[deck.id]
        summary = repo.get_deck_summary(deck.id, user_id)

        valuation = compute_deck_value(latest_prices, deck_cards)
        value_series = compute_deck_value_series(deck_cards, price_series, days=period_days)
        value_change = (
            compute_deck_value_change(value_series, period_days) if value_series else None
        )

        total_value_converted = _convert_value(valuation.total_value, converter, currency)

        # Apply value filters
        if min_value is not None and (
            total_value_converted is None or total_value_converted < min_value
        ):
            continue
        if max_value is not None and (
            total_value_converted is None or total_value_converted > max_value
        ):
            continue

        sparkline_values = [
            float(_convert_value(pt.total_value, converter, currency) or 0) for pt in value_series
        ]

        vc_abs = _convert_value(value_change.delta, converter, currency) if value_change else None
        vc_pct = float(value_change.delta_pct) if value_change else None

        entries.append(
            DeckRankingEntry(
                id=deck.id,
                name=deck.name,
                description=deck.description,
                total_cards=summary["total_cards"],
                unique_cards=summary["unique_cards"],
                owned_cards=summary["owned_cards"],
                ownership_pct=summary["ownership_pct"],
                total_value=total_value_converted,
                priced_cards=valuation.priced_cards,
                unpriced_cards=valuation.unpriced_cards,
                value_change=vc_abs,
                value_change_pct=vc_pct,
                sparkline=sparkline_values,
                currency=currency,
                created_at=deck.created_at,
                updated_at=deck.updated_at,
            )
        )

    # Sort
    reverse = sort_order == "desc"

    def sort_key(entry: DeckRankingEntry):
        if sort_by == "total_value":
            return entry.total_value if entry.total_value is not None else -1
        elif sort_by == "value_change_pct":
            return entry.value_change_pct if entry.value_change_pct is not None else -999
        elif sort_by == "value_change_abs":
            return entry.value_change if entry.value_change is not None else -999
        else:  # card_count
            return entry.total_cards

    entries.sort(key=sort_key, reverse=reverse)

    total = len(entries)
    paginated = entries[offset : offset + limit]

    return success_response(
        data=DeckRankingResponse(
            decks=paginated,
            total=total,
            sort_by=sort_by,
            period=period,
        )
    )


_VALID_FORMATS = {
    "commander",
    "standard",
    "modern",
    "legacy",
    "vintage",
    "pioneer",
    "pauper",
    "brawl",
    "oathbreaker",
    "casual",
}


@router.get("/commanders", response_model=ApiResponse[list[CommanderCandidate]])
def search_commanders(
    q: str = "",
    colors: str = "",
    limit: int = Query(default=20, ge=1, le=50),
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Search for legendary creatures that can serve as commanders."""
    from src.decks.builder import get_commander_candidates

    color_list = [c.strip().upper() for c in colors.split(",") if c.strip()] if colors else None

    candidates = get_commander_candidates(
        repo,
        colors=color_list,
        search=q if q else None,
        limit=limit,
    )

    return success_response(
        data=[CommanderCandidate(**c) for c in candidates],
    )


@router.post("/generate", response_model=ApiResponse[DeckGenerateResponse])
def generate_deck_endpoint(
    request: DeckGenerateRequest,
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Generate a deck from the catalog based on format, colors, and archetype."""
    from src.decks.builder import generate_deck
    from src.domain.models import DeckBuildParams

    fmt = request.format_name.lower()
    if fmt not in _VALID_FORMATS:
        raise api_error(
            400,
            ErrorCode.VALIDATION_ERROR,
            f"Unknown format: {request.format_name}. "
            f"Valid formats: {', '.join(sorted(_VALID_FORMATS))}",
        )

    # Validate commander if provided
    if request.commander_card_id is not None:
        commander = repo.get_card_by_id(request.commander_card_id)
        if not commander:
            raise api_error(
                400,
                ErrorCode.VALIDATION_ERROR,
                "Commander card not found in catalog",
            )
        type_line = commander.type_line or ""
        if "Legendary" not in type_line or "Creature" not in type_line:
            raise api_error(
                400,
                ErrorCode.VALIDATION_ERROR,
                f"Card '{commander.name_en}' is not a Legendary Creature",
            )

    params = DeckBuildParams(
        format_name=fmt,
        commander_card_id=request.commander_card_id,
        colors=request.colors,
        archetype=request.archetype,
        budget_limit=Decimal(str(request.budget_limit)) if request.budget_limit else None,
        prioritize_owned=request.prioritize_owned,
        user_id=user_id,
        exclude_card_ids=request.exclude_card_ids,
    )

    generated = generate_deck(repo, params)

    # Auto-generate deck name
    color_str = "".join(sorted(generated.colors)) if generated.colors else "5C"
    archetype_str = (generated.archetype or "").capitalize()
    from datetime import date as date_cls

    deck_name = request.deck_name or f"{color_str} {archetype_str} — {date_cls.today().isoformat()}"

    # Save the deck
    deck = repo.create_deck(user_id, deck_name.strip())
    cards_for_db = [
        {
            "name_en": c["name_en"],
            "set_code": c.get("set_code"),
            "collector_number": c.get("collector_number"),
            "quantity": c.get("quantity", 1),
            "card_id": c.get("card_id"),
        }
        for c in generated.cards
    ]
    repo.add_deck_cards(deck.id, cards_for_db)

    total_cards = sum(c["quantity"] for c in generated.cards)

    return success_response(
        data=DeckGenerateResponse(
            deck_id=deck.id,
            name=deck_name.strip(),
            format_name=generated.format_name,
            archetype=generated.archetype,
            colors=generated.colors,
            total_cards=total_cards,
            land_count=generated.land_count,
            nonland_count=generated.nonland_count,
            total_value=float(generated.total_value) if generated.total_value is not None else None,
            warnings=generated.warnings,
            cards=[
                GeneratedCardSchema(
                    card_id=c.get("card_id"),
                    name_en=c["name_en"],
                    set_code=c.get("set_code"),
                    collector_number=c.get("collector_number"),
                    quantity=c.get("quantity", 1),
                    mana_cost=c.get("mana_cost"),
                    type_line=c.get("type_line"),
                    rarity=c.get("rarity"),
                    image_uri=c.get("image_uri"),
                    price=c.get("price"),
                    is_owned=c.get("is_owned", False),
                )
                for c in generated.cards
            ],
        )
    )


@router.get("", response_model=ApiResponse[list[DeckSummarySchema]])
def list_decks(
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
):
    """List all decks for the authenticated user."""
    decks = repo.list_decks(user_id)

    # Collect all card_ids for batch price lookup
    all_deck_cards: dict[int, list] = {}
    all_card_ids: set[int] = set()
    for deck in decks:
        deck_cards = repo.get_deck_cards(deck.id)
        all_deck_cards[deck.id] = deck_cards
        for dc in deck_cards:
            if dc.card_id is not None:
                all_card_ids.add(dc.card_id)

    latest_prices_raw = repo.get_latest_prices_batch(list(all_card_ids)) if all_card_ids else {}
    latest_prices: dict[int, Decimal | None] = {}
    for cid, obs in latest_prices_raw.items():
        if obs and obs.median_price is not None:
            latest_prices[cid] = Decimal(str(obs.median_price))
        else:
            latest_prices[cid] = None

    data = []
    for deck in decks:
        summary = repo.get_deck_summary(deck.id, user_id)
        deck_cards = all_deck_cards[deck.id]
        valuation = compute_deck_value(latest_prices, deck_cards)

        data.append(
            DeckSummarySchema(
                id=deck.id,
                name=deck.name,
                description=deck.description,
                total_cards=summary["total_cards"],
                unique_cards=summary["unique_cards"],
                owned_cards=summary["owned_cards"],
                ownership_pct=summary["ownership_pct"],
                total_value=float(valuation.total_value)
                if valuation.total_value is not None
                else None,
                created_at=deck.created_at,
                updated_at=deck.updated_at,
            )
        )
    return success_response(data=data)


@router.get("/{deck_id}/value", response_model=ApiResponse[DeckValueDetailSchema])
def get_deck_value(
    deck_id: int,
    period: Literal["7d", "30d", "90d"] = "30d",
    currency: str = "BRL",
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Get detailed value history for a single deck."""
    deck = repo.get_deck(deck_id)
    if not deck:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Deck not found")
    if deck.user_id != user_id:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Deck not found")

    period_days = _PERIOD_DAYS.get(period, 30)
    deck_cards = repo.get_deck_cards(deck_id)

    linked_card_ids = [dc.card_id for dc in deck_cards if dc.card_id is not None]

    # Get latest prices for valuation
    latest_prices_raw = repo.get_latest_prices_batch(linked_card_ids) if linked_card_ids else {}
    latest_prices: dict[int, Decimal | None] = {}
    for cid, obs in latest_prices_raw.items():
        if obs and obs.median_price is not None:
            latest_prices[cid] = Decimal(str(obs.median_price))
        else:
            latest_prices[cid] = None

    valuation = compute_deck_value(latest_prices, deck_cards)

    # Get price series for value history
    price_series = (
        repo.get_price_series_batch(linked_card_ids, days=period_days) if linked_card_ids else {}
    )
    value_series = compute_deck_value_series(deck_cards, price_series, days=period_days)
    value_change = compute_deck_value_change(value_series, period_days) if value_series else None

    series_schemas = [
        DeckValuePointSchema(
            date=pt.date.isoformat(),
            value=float(_convert_value(pt.total_value, converter, currency) or 0),
        )
        for pt in value_series
    ]

    return success_response(
        data=DeckValueDetailSchema(
            deck_id=deck_id,
            total_value=_convert_value(valuation.total_value, converter, currency),
            priced_cards=valuation.priced_cards,
            unpriced_cards=valuation.unpriced_cards,
            value_change=_convert_value(value_change.delta, converter, currency)
            if value_change
            else None,
            value_change_pct=float(value_change.delta_pct) if value_change else None,
            value_series=series_schemas,
            currency=currency,
            period=period,
        )
    )


@router.get("/{deck_id}/evaluate", response_model=ApiResponse[DeckEvaluationResponse])
def evaluate_deck_endpoint(
    deck_id: int,
    format: str | None = Query(default=None, alias="format"),
    archetype: str | None = Query(default=None),
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Evaluate a deck: mana curve, type/color distribution, legality, budget."""
    from src.decks.evaluator import evaluate_deck

    deck = repo.get_deck(deck_id)
    if not deck:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Deck not found")
    if deck.user_id != user_id:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Deck not found")

    deck_cards = repo.get_deck_cards(deck_id)

    # Enrich cards with CardRow data (mana_cost, type_line, color_identity, rarity)
    card_ids = [dc.card_id for dc in deck_cards if dc.card_id is not None]

    # Batch-fetch card info
    card_info: dict[int, object] = {}
    for cid in card_ids:
        card_row = repo.get_card_by_id(cid)
        if card_row:
            card_info[cid] = card_row

    # Batch-fetch prices
    prices_raw = repo.get_latest_prices_batch(card_ids) if card_ids else {}
    prices: dict[int, Decimal] = {}
    for cid, obs in prices_raw.items():
        if obs and obs.median_price is not None:
            prices[cid] = Decimal(str(obs.median_price))

    # Batch-fetch legalities
    legalities = repo.get_legalities_for_cards_batch(card_ids) if card_ids else {}

    # Build enriched card dicts for the evaluator
    enriched_cards: list[dict] = []
    unlinked_count = 0
    for dc in deck_cards:
        card_dict: dict = {
            "card_id": dc.card_id,
            "name_en": dc.name_en,
            "quantity": dc.quantity,
            "mana_cost": None,
            "type_line": None,
            "color_identity": None,
            "rarity": None,
        }
        if dc.card_id is not None and dc.card_id in card_info:
            cr = card_info[dc.card_id]
            card_dict["mana_cost"] = cr.mana_cost
            card_dict["type_line"] = cr.type_line
            card_dict["color_identity"] = cr.color_identity
            card_dict["rarity"] = cr.rarity
        elif dc.card_id is None:
            unlinked_count += 1
        enriched_cards.append(card_dict)

    evaluation = evaluate_deck(
        cards=enriched_cards,
        prices=prices if prices else None,
        legalities=legalities if legalities else None,
        format_name=format,
        archetype=archetype,
    )

    # Build response
    mana_curve = [
        ManaCurvePoint(cmc=cmc, count=count) for cmc, count in sorted(evaluation.mana_curve.items())
    ]

    type_distribution = [
        TypeDistEntry(type_name=name, count=count)
        for name, count in sorted(evaluation.type_distribution.items())
    ]

    color_distribution = [
        ColorDistEntry(color=color, pip_count=count)
        for color, count in sorted(evaluation.color_distribution.items())
    ]

    legality_result = None
    if evaluation.legality_check:
        lc = evaluation.legality_check
        legality_result = LegalityResult(
            format=lc["format"],
            is_legal=lc["is_legal"],
            illegal_cards=[
                IllegalCard(name_en=ic["name_en"], status=ic["status"])
                for ic in lc.get("illegal_cards", [])
            ],
            singleton_violations=lc.get("singleton_violations", []),
            card_count_valid=lc.get("card_count_valid", True),
        )

    budget_result = None
    if evaluation.budget:
        b = evaluation.budget
        budget_result = BudgetAnalysis(
            total_value=float(b["total_value"]),
            most_expensive=[
                BudgetEntry(
                    name_en=e["name_en"],
                    price=float(e["price"]),
                    quantity=e["quantity"],
                )
                for e in b.get("most_expensive", [])
            ],
            price_tiers=b.get("price_tiers", {}),
        )

    suggestions = list(evaluation.suggestions)
    if unlinked_count > 0:
        suggestions.insert(
            0,
            f"{unlinked_count} card(s) are not linked to the catalog and "
            "were excluded from some analyses.",
        )

    return success_response(
        data=DeckEvaluationResponse(
            deck_id=deck_id,
            mana_curve=mana_curve,
            type_distribution=type_distribution,
            color_distribution=color_distribution,
            land_count=evaluation.land_count,
            nonland_count=evaluation.nonland_count,
            total_cards=evaluation.total_cards,
            avg_cmc=evaluation.avg_cmc,
            color_identity=sorted(evaluation.color_identity),
            legality=legality_result,
            budget=budget_result,
            suggestions=suggestions,
        )
    )


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
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Deck not found")
    if deck.user_id != user_id:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Deck not found")

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
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Deck not found")
    return Response(status_code=204)

"""BCB PTAX API client for fetching USD/BRL exchange rates."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import structlog

from src.domain.models import ExchangeRate

log = structlog.get_logger()

BASE_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"


def _format_date(d: date) -> str:
    """Format date as MM-DD-YYYY for the BCB API."""
    return d.strftime("%m-%d-%Y")


async def fetch_daily_rate(target_date: date | None = None) -> ExchangeRate | None:
    """Fetch a single day's USD/BRL PTAX rate from BCB.

    Returns None if the API returns an empty result (weekends/holidays)
    or if an HTTP error occurs.
    """
    if target_date is None:
        target_date = date.today()

    formatted = _format_date(target_date)
    url = f"{BASE_URL}/CotacaoDolarDia(dataCotacao=@d)" f"?@d='{formatted}'&$format=json"

    log.debug("bcb_fetch_daily", date=str(target_date), url=url)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        log.warning("bcb_fetch_error", date=str(target_date), error=str(exc))
        return None

    values = data.get("value", [])
    if not values:
        log.debug("bcb_no_data", date=str(target_date))
        return None

    cotacao_venda = values[0].get("cotacaoVenda")
    if cotacao_venda is None:
        log.warning("bcb_missing_cotacao", date=str(target_date))
        return None

    rate = Decimal(str(cotacao_venda))
    log.info("bcb_rate_fetched", date=str(target_date), rate=str(rate))

    return ExchangeRate(
        rate_date=target_date,
        from_currency="USD",
        to_currency="BRL",
        rate=rate,
        source="bcb_ptax",
    )


async def fetch_rate_range(start: date, end: date) -> list[ExchangeRate]:
    """Fetch USD/BRL PTAX rates for a date range from BCB.

    Returns a list of ExchangeRate objects for each business day in the range.
    """
    start_fmt = _format_date(start)
    end_fmt = _format_date(end)
    url = (
        f"{BASE_URL}/CotacaoDolarPeriodo(dataInicial=@di,dataFinalCotacao=@df)"
        f"?@di='{start_fmt}'&@df='{end_fmt}'&$format=json"
    )

    log.debug("bcb_fetch_range", start=str(start), end=str(end), url=url)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        log.warning(
            "bcb_fetch_range_error",
            start=str(start),
            end=str(end),
            error=str(exc),
        )
        return []

    values = data.get("value", [])
    results: list[ExchangeRate] = []
    for entry in values:
        cotacao_venda = entry.get("cotacaoVenda")
        data_cotacao = entry.get("dataHoraCotacao", "")
        if cotacao_venda is None or not data_cotacao:
            continue

        # dataHoraCotacao format: "2026-08-20 13:11:10.123"
        rate_date = date.fromisoformat(data_cotacao[:10])
        rate = Decimal(str(cotacao_venda))

        results.append(
            ExchangeRate(
                rate_date=rate_date,
                from_currency="USD",
                to_currency="BRL",
                rate=rate,
                source="bcb_ptax",
            )
        )

    log.info(
        "bcb_range_fetched",
        start=str(start),
        end=str(end),
        count=len(results),
    )
    return results

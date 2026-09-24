"""Tests for F176-T06: automatic daily snapshot at the end of liga-sweep."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.collectors.liga_sweep import LigaSweepResult, run_liga_sweep
from src.collectors.price_snapshot import SNAPSHOT_SOURCE
from src.database.models import Base, PriceObservationRow
from src.database.repository import Repository

SNAPSHOT_PATH = "src.collectors.price_snapshot.run_daily_snapshot"

# ── Helpers ──────────────────────────────────────────────────────────


def _make_card(card_id: int, name_en: str) -> dict:
    return {
        "entry_id": card_id,
        "card_id": card_id,
        "name_en": name_en,
        "name_pt": name_en,
        "set_code": "DMU",
        "collector_number": str(card_id),
    }


def _mock_provider_search(prices_map: dict | None = None):
    """Mock provider whose search_card returns ``normal.mid`` from a map."""
    provider = AsyncMock()
    provider.open = AsyncMock()
    provider.close = AsyncMock()

    async def _search(name, **kwargs):
        price = prices_map.get(name) if prices_map is not None else Decimal("1.50")
        return {
            "normal": {"low": None, "mid": price, "high": None},
            "page_url": "https://www.ligamagic.com.br/?view=cards/card&card=x&show=1",
        }

    provider.search_card = AsyncMock(side_effect=_search)
    return provider


async def _run(mock_repo, provider=None, **kwargs) -> LigaSweepResult:
    provider = provider or _mock_provider_search()
    with (
        patch("src.collectors.liga_sweep.Repository", return_value=mock_repo),
        patch("src.collectors.liga_sweep.get_db_url", return_value="sqlite:///:memory:"),
        patch("src.providers.liga.provider.LigaMagicProvider", return_value=provider),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        return await run_liga_sweep(db_url="sqlite:///:memory:", delay=0, **kwargs)


def _mock_repo(n_cards: int) -> MagicMock:
    repo = MagicMock()
    repo.get_cards_for_liga_scan.return_value = [
        _make_card(i, f"Card {i}") for i in range(1, n_cards + 1)
    ]
    repo.insert_price_observations.return_value = 1
    return repo


# ── Unit ─────────────────────────────────────────────────────────────


def test_result_default_daily_snapshot_created_is_zero():
    result = LigaSweepResult(
        total_eligible=0,
        total_processed=0,
        prices_found=0,
        prices_not_found=0,
        errors=0,
        batches_completed=0,
        dry_run=False,
    )
    assert result.daily_snapshot_created == 0


@pytest.mark.asyncio
async def test_snapshot_called_once_after_processing():
    repo = _mock_repo(2)
    with patch(SNAPSHOT_PATH, return_value=7) as mock_snapshot:
        result = await _run(repo)

    mock_snapshot.assert_called_once_with(repo)
    assert result.total_processed == 2
    assert result.daily_snapshot_created == 7


@pytest.mark.asyncio
async def test_snapshot_logged_with_count():
    repo = _mock_repo(1)
    with (
        patch(SNAPSHOT_PATH, return_value=3),
        patch("src.collectors.liga_sweep.log") as mock_log,
    ):
        await _run(repo)

    mock_log.info.assert_any_call("liga_sweep_daily_snapshot", created=3)


@pytest.mark.asyncio
async def test_dry_run_skips_snapshot():
    repo = _mock_repo(3)
    with patch(SNAPSHOT_PATH, return_value=5) as mock_snapshot:
        result = await _run(repo, dry_run=True)

    mock_snapshot.assert_not_called()
    assert result.daily_snapshot_created == 0


@pytest.mark.asyncio
async def test_snapshot_after_false_skips_snapshot():
    repo = _mock_repo(3)
    with patch(SNAPSHOT_PATH, return_value=5) as mock_snapshot:
        result = await _run(repo, snapshot_after=False)

    mock_snapshot.assert_not_called()
    assert result.total_processed == 3
    assert result.daily_snapshot_created == 0


@pytest.mark.asyncio
async def test_zero_eligible_skips_snapshot():
    repo = _mock_repo(0)
    with patch(SNAPSHOT_PATH, return_value=5) as mock_snapshot:
        result = await _run(repo)

    mock_snapshot.assert_not_called()
    assert result.total_processed == 0
    assert result.daily_snapshot_created == 0


@pytest.mark.asyncio
async def test_snapshot_runs_when_only_not_found_or_errors():
    """Processed counts cards attempted, not only prices found."""
    repo = _mock_repo(2)
    provider = _mock_provider_search({"Card 1": None, "Card 2": None})
    with patch(SNAPSHOT_PATH, return_value=4) as mock_snapshot:
        result = await _run(repo, provider=provider)

    mock_snapshot.assert_called_once()
    assert result.prices_found == 0
    assert result.daily_snapshot_created == 4


@pytest.mark.asyncio
async def test_snapshot_failure_does_not_raise_or_change_counts():
    repo = _mock_repo(2)
    with (
        patch(SNAPSHOT_PATH, side_effect=RuntimeError("neon down")),
        patch("src.collectors.liga_sweep.log") as mock_log,
    ):
        result = await _run(repo)

    assert result.total_eligible == 2
    assert result.total_processed == 2
    assert result.prices_found == 2
    assert result.errors == 0
    assert result.daily_snapshot_created == 0
    mock_log.warning.assert_any_call("liga_sweep_daily_snapshot_failed", error="neon down")


@pytest.mark.asyncio
async def test_on_complete_failure_still_runs_snapshot():
    repo = _mock_repo(2)
    on_complete = MagicMock(side_effect=ValueError("hook boom"))
    with patch(SNAPSHOT_PATH, return_value=2) as mock_snapshot:
        result = await _run(repo, on_complete=on_complete)

    on_complete.assert_called_once()
    mock_snapshot.assert_called_once_with(repo)
    assert result.daily_snapshot_created == 2


@pytest.mark.asyncio
async def test_snapshot_runs_after_on_complete():
    repo = _mock_repo(1)
    order: list[str] = []
    on_complete = MagicMock(side_effect=lambda *_: order.append("on_complete"))

    def _snap(_repo):
        order.append("snapshot")
        return 0

    with patch(SNAPSHOT_PATH, side_effect=_snap):
        await _run(repo, on_complete=on_complete)

    assert order == ["on_complete", "snapshot"]


@pytest.mark.asyncio
async def test_keyboard_interrupt_after_processing_still_snapshots():
    repo = _mock_repo(3)
    provider = _mock_provider_search()
    calls = {"n": 0}

    async def _search(name, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise KeyboardInterrupt
        return {"normal": {"low": None, "mid": Decimal("1.00"), "high": None}}

    provider.search_card = AsyncMock(side_effect=_search)
    with patch(SNAPSHOT_PATH, return_value=1) as mock_snapshot:
        result = await _run(repo, provider=provider)

    assert result.total_processed == 1
    mock_snapshot.assert_called_once()
    assert result.daily_snapshot_created == 1


@pytest.mark.asyncio
async def test_keyboard_interrupt_before_processing_skips_snapshot():
    repo = _mock_repo(2)
    provider = _mock_provider_search()
    provider.search_card = AsyncMock(side_effect=KeyboardInterrupt)
    with patch(SNAPSHOT_PATH, return_value=1) as mock_snapshot:
        result = await _run(repo, provider=provider)

    assert result.total_processed == 0
    mock_snapshot.assert_not_called()


# ── Integration (real SQLite) ────────────────────────────────────────


@pytest.fixture
def sqlite_repo():
    r = Repository(db_url="sqlite:///:memory:")
    Base.metadata.create_all(r.engine)
    return r


def _rows_on(repo: Repository, day: date) -> set[tuple[str, str, Decimal]]:
    stmt = select(
        PriceObservationRow.source,
        PriceObservationRow.external_id,
        PriceObservationRow.median_price,
    ).where(PriceObservationRow.observed_at == day)
    with Session(repo.engine) as session:
        return {(r[0], r[1], Decimal(str(r[2]))) for r in session.execute(stmt).all()}


@pytest.mark.asyncio
async def test_integration_sweep_writes_daily_snapshot(sqlite_repo):
    today = date.today()
    with Session(sqlite_repo.engine) as session:
        session.add(
            PriceObservationRow(
                source="liga",
                external_id="liga_2",
                observed_at=today - timedelta(days=3),
                median_price=Decimal("7.50"),
            )
        )
        session.commit()

    cards = [_make_card(1, "Card A"), _make_card(2, "Card B")]
    provider = _mock_provider_search({"Card A": Decimal("10"), "Card B": None})

    with patch.object(sqlite_repo, "get_cards_for_liga_scan", return_value=cards):
        result = await _run(sqlite_repo, provider=provider)

    assert result.prices_found == 1
    assert result.daily_snapshot_created == 1

    rows = _rows_on(sqlite_repo, today)
    # A: real Liga observation today, no synthetic snapshot on top of it.
    assert ("liga", "liga_1", Decimal("10")) in rows
    assert not any(s == SNAPSHOT_SOURCE and e == "liga_1" for s, e, _ in rows)
    # B: carried forward from its 3-day-old real price.
    snapshot_b = [p for s, e, p in rows if s == SNAPSHOT_SOURCE and e == "liga_2"]
    assert snapshot_b == [Decimal("7.50")]

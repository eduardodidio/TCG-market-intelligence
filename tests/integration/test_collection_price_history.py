"""F176-T12: end-to-end integration test for the collection price history pipeline.

Exercises the real pipeline — Liga sweep with a fake provider, daily
snapshot / backfill, and the collection + card history endpoints — on a
file-based SQLite database, with no network access.

Governance note (ADR 0017): F175's market trending excludes foil cards;
this file only asserts collection/card *history* behavior (AC3, AC4, AC11,
AC12), which is unaffected by that exclusion, so no assertion here relies
on the old (pre-ADR-0017) foil-inclusive trending behavior.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.cards import router as cards_router
from src.api.routers.collection import router as collection_router
from src.collectors.liga_sweep import run_liga_sweep
from src.collectors.price_snapshot import SNAPSHOT_SOURCE, backfill_snapshots, run_daily_snapshot
from src.database.models import CardRow, PriceObservationRow, UserCollectionRow
from src.database.repository import Repository
from src.services.currency import CurrencyConverter

TODAY = date.today()
_USER = "eduardo"

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_url(tmp_path) -> str:
    return f"sqlite:///{tmp_path / 'f176.db'}"


@pytest.fixture()
def repo(db_url) -> Repository:
    return Repository(db_url=db_url)


@pytest.fixture()
def client(repo) -> TestClient:
    app = FastAPI()
    app.include_router(cards_router, prefix="/api/v1")
    app.include_router(collection_router, prefix="/api/v1")

    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: _USER
    app.dependency_overrides[get_currency_converter_dep] = lambda: CurrencyConverter(repo)
    return TestClient(app)


def _make_card(repo: Repository, name: str = "Card", collector_number: str = "1") -> int:
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic", name_en=name, set_code="TST", collector_number=collector_number
        )
        session.add(card)
        session.commit()
        return card.id


def _make_collection_entry(
    repo: Repository,
    card_id: int | None,
    *,
    user_id: str = _USER,
    extras: str | None = None,
    collector_number: str = "1",
    name_en: str | None = None,
) -> int:
    with Session(repo.engine) as session:
        entry = UserCollectionRow(
            user_id=user_id,
            card_id=card_id,
            set_code="TST",
            collector_number=collector_number,
            extras=extras,
            name_en=name_en,
        )
        session.add(entry)
        session.commit()
        return entry.id


def _add_observation(
    repo: Repository,
    source: str,
    external_id: str,
    observed_at: date,
    median_price,
    currency: str = "BRL",
) -> None:
    with Session(repo.engine) as session:
        session.add(
            PriceObservationRow(
                source=source,
                external_id=external_id,
                observed_at=observed_at,
                median_price=Decimal(str(median_price)) if median_price is not None else None,
                currency=currency,
            )
        )
        session.commit()


def _observations_on(repo: Repository, day: date) -> list[tuple[str, str, Decimal]]:
    with Session(repo.engine) as session:
        rows = (
            session.query(PriceObservationRow)
            .filter(PriceObservationRow.observed_at == day)
            .all()
        )
        return [(r.source, r.external_id, r.median_price) for r in rows]


def _mock_provider(prices_map: dict[str, dict] | None = None):
    """Fake Liga provider. ``prices_map``: card_name -> {"normal": mid, "foil": mid}."""
    provider = AsyncMock()
    provider.open = AsyncMock()
    provider.close = AsyncMock()

    async def _search(name, **kwargs):
        entry = (prices_map or {}).get(name, {})
        normal_mid = entry.get("normal", Decimal("1.50"))
        foil_mid = entry.get("foil")
        return {
            "normal": {"low": None, "mid": normal_mid, "high": None},
            "foil": {"low": None, "mid": foil_mid, "high": None},
            "page_url": "https://www.ligamagic.com.br/?view=cards/card&card=x&show=1",
        }

    provider.search_card = AsyncMock(side_effect=_search)
    return provider


async def _run_sweep(db_url: str, prices_map: dict | None = None, **kwargs):
    """Run the real ``run_liga_sweep`` against *db_url* with a fake provider.

    No network access: the Liga provider constructor and ``asyncio.sleep``
    are patched, everything else (repository queries, snapshot writing)
    runs for real against the SQLite file.
    """
    provider = _mock_provider(prices_map)
    with (
        patch("src.providers.liga.provider.LigaMagicProvider", return_value=provider),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        return await run_liga_sweep(
            db_url=db_url,
            delay=0,
            batch_pause=0,
            collection_only=True,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Normal card
# ---------------------------------------------------------------------------


class TestNormalCardHistory:
    @pytest.mark.asyncio
    async def test_full_pipeline_yields_daily_points(self, repo, db_url, client):
        card_id = _make_card(repo, "Normal Pipeline Card")
        _make_collection_entry(repo, card_id, name_en="Normal Pipeline Card")

        # Two real historical observations, no source_cards row (Liga-only path).
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=20), "10.00")
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=10), "12.00")

        result = await _run_sweep(db_url, {"Normal Pipeline Card": {"normal": Decimal("15.00")}})
        assert result.prices_found == 1

        backfill_snapshots(repo, days=30)

        resp = client.get(f"/api/v1/collection/{_entry_id_for(repo, card_id)}/history?period=30d")
        assert resp.status_code == 200
        observations = resp.json()["data"]["observations"]

        assert len(observations) >= 21  # D-20..D inclusive
        dates = [o["observed_at"] for o in observations]
        assert min(dates) == str(TODAY - timedelta(days=20))
        assert len(dates) == len(set(dates))  # one point per day
        assert observations[-1]["median_price"] == "15.00"


def _entry_id_for(repo: Repository, card_id: int) -> int:
    with Session(repo.engine) as session:
        row = (
            session.query(UserCollectionRow).filter(UserCollectionRow.card_id == card_id).first()
        )
        return row.id


# ---------------------------------------------------------------------------
# Foil card
# ---------------------------------------------------------------------------


class TestFoilCardHistory:
    @pytest.mark.asyncio
    async def test_foil_entry_only_sees_foil_series(self, repo, db_url, client):
        card_id = _make_card(repo, "Foil Pipeline Card")
        entry_id = _make_collection_entry(
            repo, card_id, extras="Foil", name_en="Foil Pipeline Card"
        )

        result = await _run_sweep(
            db_url,
            {"Foil Pipeline Card": {"normal": Decimal("5.00"), "foil": Decimal("500.00")}},
        )
        assert result.prices_found == 1

        resp = client.get(f"/api/v1/collection/{entry_id}/history?period=30d")
        assert resp.status_code == 200
        body = resp.json()["data"]

        prices = [o["median_price"] for o in body["observations"]]
        assert prices == ["500.00"]
        assert body["meta"]["variant"] == "foil"


# ---------------------------------------------------------------------------
# Daily recording (post-sweep snapshot)
# ---------------------------------------------------------------------------


class TestDailyRecording:
    @pytest.mark.asyncio
    async def test_sweep_creates_snapshot_for_series_without_collection_today(
        self, repo, db_url
    ):
        # Card A is swept today (real liga obs); card B already has a real
        # obs from 3 days ago and is skipped by max_age_days=7 -> it needs
        # a carry-forward snapshot instead.
        card_a = _make_card(repo, "Sweep Card A", collector_number="1")
        card_b = _make_card(repo, "Sweep Card B", collector_number="2")
        _make_collection_entry(
            repo, card_a, collector_number="1", name_en="Sweep Card A"
        )
        _make_collection_entry(
            repo, card_b, collector_number="2", name_en="Sweep Card B"
        )
        _add_observation(
            repo, "liga", f"liga_{card_b}", TODAY - timedelta(days=3), "7.50"
        )

        result = await _run_sweep(
            db_url, {"Sweep Card A": {"normal": Decimal("10.00")}, "Sweep Card B": {"normal": None}}
        )

        assert result.daily_snapshot_created == 1
        today_rows = _observations_on(repo, TODAY)
        assert (
            "liga",
            f"liga_{card_a}",
            Decimal("10.00"),
        ) in today_rows
        snapshot_rows = [
            r for r in today_rows if r[0] == SNAPSHOT_SOURCE and r[1] == f"liga_{card_b}"
        ]
        assert snapshot_rows == [(SNAPSHOT_SOURCE, f"liga_{card_b}", Decimal("7.50"))]

    def test_second_snapshot_same_day_does_not_duplicate(self, repo):
        card_id = _make_card(repo, "Dup Card")
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=3), "9.00")

        first = run_daily_snapshot(repo)
        second = run_daily_snapshot(repo)

        assert first == 1
        assert second == 0
        assert len(_observations_on(repo, TODAY)) == 1


# ---------------------------------------------------------------------------
# Cross-endpoint consistency
# ---------------------------------------------------------------------------


class TestCrossEndpointConsistency:
    def test_collection_and_card_history_agree_for_normal_variant(self, repo, client):
        card_id = _make_card(repo, "Consistent Card")
        entry_id = _make_collection_entry(repo, card_id)
        for i in range(5):
            _add_observation(
                repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=i), f"{10 + i}.00"
            )

        collection_resp = client.get(f"/api/v1/collection/{entry_id}/history?period=30d")
        card_resp = client.get(f"/api/v1/cards/{card_id}/history?period=30d")

        assert collection_resp.status_code == 200
        assert card_resp.status_code == 200

        collection_obs = collection_resp.json()["data"]["observations"]
        card_obs = card_resp.json()["data"]["observations"]

        collection_points = {(o["observed_at"], o["median_price"]) for o in collection_obs}
        card_points = {(o["observed_at"], o["median_price"]) for o in card_obs}
        assert collection_points == card_points

    def test_collection_metrics_has_positive_data_points(self, repo, client):
        card_id = _make_card(repo, "Metrics Card")
        entry_id = _make_collection_entry(repo, card_id)
        for i in range(3):
            _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=i), "20.00")

        resp = client.get(f"/api/v1/collection/{entry_id}/metrics?period=30d")

        assert resp.status_code == 200
        assert resp.json()["data"]["data_points"] > 0


# ---------------------------------------------------------------------------
# Edge / boundary / idempotency scenarios
# ---------------------------------------------------------------------------


class TestHistoryEdgeCases:
    def test_linked_entry_without_prices_has_empty_observations(self, repo, client):
        card_id = _make_card(repo, "No Price Card")
        entry_id = _make_collection_entry(repo, card_id)

        resp = client.get(f"/api/v1/collection/{entry_id}/history?period=30d")

        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["observations"] == []
        assert body["meta"]["first_observed_at"] is None

    def test_unlinked_entry_has_empty_observations(self, repo, client):
        entry_id = _make_collection_entry(repo, None)

        resp = client.get(f"/api/v1/collection/{entry_id}/history?period=30d")

        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["observations"] == []

    def test_other_users_entry_returns_404(self, repo, client):
        card_id = _make_card(repo, "Owned By Other")
        entry_id = _make_collection_entry(repo, card_id, user_id="someone-else")

        resp = client.get(f"/api/v1/collection/{entry_id}/history?period=30d")

        assert resp.status_code == 404

    def test_24h_period_only_returns_recent_points(self, repo, client):
        card_id = _make_card(repo, "24h Card")
        entry_id = _make_collection_entry(repo, card_id)
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY, "10.00")
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=1), "9.00")
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=10), "5.00")

        resp = client.get(f"/api/v1/collection/{entry_id}/history?period=24h")

        assert resp.status_code == 200
        dates = {o["observed_at"] for o in resp.json()["data"]["observations"]}
        assert dates <= {str(TODAY), str(TODAY - timedelta(days=1))}
        assert str(TODAY - timedelta(days=10)) not in dates

    def test_1y_period_uses_weekly_resolution_without_error(self, repo, client):
        card_id = _make_card(repo, "1y Card")
        entry_id = _make_collection_entry(repo, card_id)
        for i in range(0, 200, 10):
            _add_observation(
                repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=i), "10.00"
            )

        resp = client.get(f"/api/v1/collection/{entry_id}/history?period=1y")

        assert resp.status_code == 200
        assert resp.json()["data"]["summary"]["resolution"] == "weekly"

    def test_backfill_is_idempotent(self, repo):
        card_id = _make_card(repo, "Idempotent Card")
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=15), "10.00")

        first = backfill_snapshots(repo, days=30)
        second = backfill_snapshots(repo, days=30)

        assert first > 0
        assert second == 0

    def test_snapshot_is_idempotent(self, repo):
        card_id = _make_card(repo, "Idempotent Snapshot Card")
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=2), "10.00")

        first = run_daily_snapshot(repo)
        second = run_daily_snapshot(repo)

        assert first == 1
        assert second == 0

    def test_carry_forward_stops_after_max_days(self, repo, client):
        card_id = _make_card(repo, "Carry Forward Card")
        entry_id = _make_collection_entry(repo, card_id)
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=40), "8.00")

        backfill_snapshots(repo, days=90)

        resp = client.get(f"/api/v1/collection/{entry_id}/history?period=90d")
        dates = {o["observed_at"] for o in resp.json()["data"]["observations"]}

        assert str(TODAY - timedelta(days=40)) in dates
        assert str(TODAY - timedelta(days=10)) in dates
        for d in range(0, 9):
            assert str(TODAY - timedelta(days=d)) not in dates


# ---------------------------------------------------------------------------
# Regression guards (H1, H2, H4, H5, H6)
# ---------------------------------------------------------------------------


class TestRegressionGuards:
    def test_h1_liga_only_card_has_history(self, repo, client):
        """H1: pre-F176, the endpoint only looked at ``source_cards`` rows,
        so a card whose only prices came from the Liga sweep (which writes
        directly to ``price_observations`` without a ``source_cards`` row)
        had an always-empty history. This must now return points.
        """
        card_id = _make_card(repo, "H1 Liga Only Card")
        entry_id = _make_collection_entry(repo, card_id)
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=1), "10.00")

        resp = client.get(f"/api/v1/collection/{entry_id}/history?period=30d")

        assert resp.status_code == 200
        assert len(resp.json()["data"]["observations"]) == 1

    def test_h2_daily_snapshot_source_included(self, repo, client):
        """H2: pre-F176, the endpoint filtered to
        ``source IN [sc.source, 'jsonld_snapshot']`` and never included
        ``daily_snapshot`` rows, so F168's carry-forward points never
        reached the collection chart.
        """
        card_id = _make_card(repo, "H2 Snapshot Card")
        entry_id = _make_collection_entry(repo, card_id)
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=5), "10.00")
        _add_observation(
            repo, "daily_snapshot", f"liga_{card_id}", TODAY - timedelta(days=2), "10.00"
        )

        resp = client.get(f"/api/v1/collection/{entry_id}/history?period=30d")

        sources = {o["source"] for o in resp.json()["data"]["observations"]}
        assert "daily_snapshot" in sources

    def test_h4_foil_and_normal_series_do_not_mix(self, repo, client):
        """H4: pre-F176, all series of a ``card_id`` were merged regardless
        of the entry's ``extras`` (foil flag), so a foil entry's chart
        zig-zagged between foil and normal prices.
        """
        card_id = _make_card(repo, "H4 Foil Mix Card")
        entry_id = _make_collection_entry(repo, card_id, extras="Foil")
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=1), "10.00")
        _add_observation(repo, "liga", f"liga_{card_id}_foil", TODAY - timedelta(days=1), "300.00")

        resp = client.get(f"/api/v1/collection/{entry_id}/history?period=30d")

        prices = {o["median_price"] for o in resp.json()["data"]["observations"]}
        assert prices == {"300.00"}

    def test_h5_same_day_observations_are_deduplicated(self, repo, client):
        """H5: pre-F176, multiple same-day observations from different
        sources (liga + daily_snapshot) were concatenated without dedup,
        producing more than one point per day.
        """
        card_id = _make_card(repo, "H5 Dedup Card")
        entry_id = _make_collection_entry(repo, card_id)
        _add_observation(repo, "liga", f"liga_{card_id}", TODAY - timedelta(days=1), "10.00")
        _add_observation(
            repo, "daily_snapshot", f"liga_{card_id}", TODAY - timedelta(days=1), "10.00"
        )

        resp = client.get(f"/api/v1/collection/{entry_id}/history?period=30d")

        observations = resp.json()["data"]["observations"]
        dates = [o["observed_at"] for o in observations]
        assert len(dates) == len(set(dates))

    def test_h6_backfill_never_creates_points_before_first_real_observation(self, repo, client):
        """H6: pre-F176, ``backfill_snapshots`` replicated the *current*
        price for every day in the window, including days before any real
        observation existed for the card -- fabricated history.
        """
        card_id = _make_card(repo, "H6 Backfill Card")
        entry_id = _make_collection_entry(repo, card_id)
        first_real = TODAY - timedelta(days=10)
        _add_observation(repo, "liga", f"liga_{card_id}", first_real, "10.00")

        backfill_snapshots(repo, days=30)

        resp = client.get(f"/api/v1/collection/{entry_id}/history?period=30d")
        dates = {o["observed_at"] for o in resp.json()["data"]["observations"]}

        assert all(date.fromisoformat(d) >= first_real for d in dates)

"""Tests for src.services.collection_price_history (F176-T07)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from src.api.schemas.collection import PriceHistoryMeta
from src.collection.price_history_keys import SNAPSHOT_SOURCE, SeriesKey
from src.collectors.price_snapshot import BACKFILL_SOURCE
from src.database.models import Base, CardRow, PriceObservationRow, SourceCardRow
from src.database.repository import Repository
from src.services.collection_price_history import (
    build_history,
    first_real_observation,
    load_series,
)

TODAY = date(2026, 9, 24)


def D(n: int) -> date:  # noqa: N802 — reads like the test plan ("D-5")
    return TODAY - timedelta(days=n)


@pytest.fixture
def repo() -> Repository:
    r = Repository("sqlite:///:memory:")
    Base.metadata.create_all(r.engine)
    return r


def _card(repo: Repository, number: str = "7", source_cards: list[tuple[str, str]] = ()) -> int:
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic", name_en=f"Card {number}", set_code="TST", collector_number=number
        )
        session.add(card)
        session.flush()
        for source, ext in source_cards:
            session.add(
                SourceCardRow(
                    source=source,
                    external_id=ext,
                    card_id=card.id,
                    url=f"https://example.com/{ext}",
                )
            )
        session.commit()
        return card.id


def _obs(repo: Repository, source: str, ext: str, day: date, price: str | None) -> None:
    with Session(repo.engine) as session:
        session.add(
            PriceObservationRow(
                source=source,
                external_id=ext,
                observed_at=day,
                median_price=Decimal(price) if price is not None else None,
                currency="BRL",
            )
        )
        session.commit()


def _count_obs_selects(repo: Repository) -> list[str]:
    statements: list[str] = []

    @event.listens_for(repo.engine, "before_cursor_execute")
    def _capture(conn, cursor, statement, params, context, executemany):  # noqa: ARG001
        if statement.lstrip().upper().startswith("SELECT") and "price_observations" in statement:
            statements.append(statement)

    return statements


# ---------------------------------------------------------------------------
# build_history
# ---------------------------------------------------------------------------


def test_liga_only_card_includes_daily_snapshot(repo):
    """H1 + H2: card without source_cards still gets liga + daily_snapshot points."""
    cid = _card(repo)
    for n in (5, 3, 1):
        _obs(repo, "liga", f"liga_{cid}", D(n), "10")
    for n in (4, 2, 0):
        _obs(repo, SNAPSHOT_SOURCE, f"liga_{cid}", D(n), "10")

    series, meta = build_history(repo, cid, is_foil=False, days=30, today=TODAY)

    assert [p.observed_at for p in series] == [D(5), D(4), D(3), D(2), D(1), D(0)]
    assert meta == {
        "variant": "normal",
        "sources": ["liga", SNAPSHOT_SOURCE],
        "first_observed_at": D(5),
        "last_observed_at": D(0),
        "real_points": 3,
        "snapshot_points": 3,
    }
    PriceHistoryMeta(**meta)  # compatible with the API schema


def test_liga_beats_myp_same_day(repo):
    cid = _card(repo, source_cards=[("myp", "myp_99")])
    _obs(repo, "myp", "myp_99", D(2), "20")
    _obs(repo, "liga", f"liga_{cid}", D(2), "15")
    _obs(repo, "myp", "myp_99", D(1), "21")

    series, meta = build_history(repo, cid, is_foil=False, days=None, today=TODAY)

    assert [(p.observed_at, p.source) for p in series] == [(D(2), "liga"), (D(1), "myp")]
    assert meta["sources"] == ["liga", "myp"]
    assert meta["real_points"] == 2


def test_foil_isolated_from_normal(repo):
    """H4: foil series never mixes with normal prices."""
    cid = _card(repo)
    for n in (3, 2, 1):
        _obs(repo, "liga", f"liga_{cid}_foil", D(n), "100")
        _obs(repo, "liga", f"liga_{cid}", D(n), "10")

    series, meta = build_history(repo, cid, is_foil=True, days=30, today=TODAY)

    assert len(series) == 3
    assert {p.median_price for p in series} == {Decimal("100")}
    assert meta["variant"] == "foil"

    normal, normal_meta = build_history(repo, cid, is_foil=False, days=30, today=TODAY)
    assert {p.median_price for p in normal} == {Decimal("10")}
    assert normal_meta["variant"] == "normal"


def test_manual_beats_liga_same_day(repo):
    cid = _card(repo)
    _obs(repo, "liga", f"liga_{cid}", D(1), "10")
    _obs(repo, "manual", f"manual_{cid}", D(1), "12")

    series, meta = build_history(repo, cid, is_foil=False, days=None, today=TODAY)

    assert len(series) == 1  # H5: 1 point per day
    assert series[0].source == "manual"
    assert series[0].median_price == Decimal("12")
    assert meta["sources"] == ["manual"]


def test_period_filter_keeps_first_observed_at(repo):
    cid = _card(repo)
    _obs(repo, "liga", f"liga_{cid}", D(10), "8")
    _obs(repo, "liga", f"liga_{cid}", D(3), "9")

    series, meta = build_history(repo, cid, is_foil=False, days=7, today=TODAY)

    assert [p.observed_at for p in series] == [D(3)]
    assert meta["first_observed_at"] == D(10)
    assert meta["last_observed_at"] == D(3)


def test_days_none_returns_all_history(repo):
    cid = _card(repo)
    _obs(repo, "liga", f"liga_{cid}", D(400), "8")
    _obs(repo, "liga", f"liga_{cid}", D(3), "9")

    series, _ = build_history(repo, cid, is_foil=False, days=None, today=TODAY)

    assert [p.observed_at for p in series] == [D(400), D(3)]


def test_no_observations(repo):
    cid = _card(repo, source_cards=[("myp", "myp_1")])

    series, meta = build_history(repo, cid, is_foil=False, days=30, today=TODAY)

    assert series == []
    assert meta == {
        "variant": "normal",
        "sources": [],
        "first_observed_at": None,
        "last_observed_at": None,
        "real_points": 0,
        "snapshot_points": 0,
    }


def test_only_snapshots_have_no_first_real_observation(repo):
    cid = _card(repo)
    _obs(repo, SNAPSHOT_SOURCE, f"liga_{cid}", D(2), "10")
    _obs(repo, BACKFILL_SOURCE, f"liga_{cid}", D(1), "10")

    series, meta = build_history(repo, cid, is_foil=False, days=30, today=TODAY)

    assert [p.source for p in series] == [SNAPSHOT_SOURCE, BACKFILL_SOURCE]
    assert meta["first_observed_at"] is None
    assert meta["real_points"] == 0
    assert meta["snapshot_points"] == 2


def test_other_card_key_never_appears(repo):
    cid = _card(repo, "7")
    other = _card(repo, "8")
    _obs(repo, "liga", f"liga_{cid}", D(1), "10")
    _obs(repo, "liga", f"liga_{other}", D(1), "99")
    _obs(repo, "liga", f"liga_{other}", D(2), "99")
    _obs(repo, SNAPSHOT_SOURCE, f"liga_{other}", D(3), "99")

    series, meta = build_history(repo, cid, is_foil=False, days=None, today=TODAY)

    assert [p.external_id for p in series] == [f"liga_{cid}"]
    assert meta["first_observed_at"] == D(1)


def test_single_point_and_inclusive_cutoff(repo):
    cid = _card(repo)
    _obs(repo, "liga", f"liga_{cid}", D(7), "10")  # exactly on the cutoff
    _obs(repo, "liga", f"liga_{cid}", D(8), "11")  # one day before

    series, meta = build_history(repo, cid, is_foil=False, days=7, today=TODAY)

    assert len(series) == 1
    assert series[0].observed_at == D(7)
    assert meta["real_points"] == 1
    assert meta["first_observed_at"] == D(8)


def test_null_price_ignored(repo):
    cid = _card(repo)
    _obs(repo, "liga", f"liga_{cid}", D(2), None)
    _obs(repo, "liga", f"liga_{cid}", D(1), "10")

    series, meta = build_history(repo, cid, is_foil=False, days=None, today=TODAY)

    assert [p.observed_at for p in series] == [D(1)]
    assert meta["first_observed_at"] == D(1)


def test_catalog_source_card_and_jsonld_snapshot_included(repo):
    cid = _card(repo, source_cards=[("liga", "liga_catalog_TST_7"), ("myp", "myp_5")])
    _obs(repo, "liga", "liga_catalog_TST_7", D(3), "10")
    _obs(repo, "jsonld_snapshot", "myp_5", D(2), "11")
    _obs(repo, SNAPSHOT_SOURCE, "myp_5", D(1), "11")

    series, meta = build_history(repo, cid, is_foil=False, days=None, today=TODAY)

    assert [p.source for p in series] == ["liga", "jsonld_snapshot", SNAPSHOT_SOURCE]
    assert meta["sources"] == ["liga", "jsonld_snapshot", SNAPSHOT_SOURCE]


def test_build_history_uses_single_observation_query(repo):
    cid = _card(repo, source_cards=[("myp", "myp_1"), ("myp", "myp_2")])
    _obs(repo, "liga", f"liga_{cid}", D(1), "10")
    _obs(repo, "myp", "myp_2", D(2), "11")

    statements = _count_obs_selects(repo)
    build_history(repo, cid, is_foil=False, days=30, today=TODAY)

    # One for load_series, one for first_real_observation's MIN().
    assert len(statements) == 2
    assert sum("min(" in s.lower() for s in statements) == 1


def test_invalid_card_id_raises(repo):
    with pytest.raises(ValueError):
        build_history(repo, 0, is_foil=False, days=30, today=TODAY)


# ---------------------------------------------------------------------------
# load_series / first_real_observation
# ---------------------------------------------------------------------------


def test_load_series_single_query_and_ordering(repo):
    _obs(repo, "liga", "liga_1", D(1), "10")
    _obs(repo, "myp", "myp_1", D(3), "12")
    _obs(repo, SNAPSHOT_SOURCE, "liga_1", D(2), "10")
    keys = [
        SeriesKey("liga", "liga_1"),
        SeriesKey("myp", "myp_1"),
        SeriesKey(SNAPSHOT_SOURCE, "liga_1"),
    ]

    statements = _count_obs_selects(repo)
    rows = load_series(repo, keys, days=None)

    assert len(statements) == 1
    assert [r.observed_at for r in rows] == [D(3), D(2), D(1)]
    assert rows[0].median_price == Decimal("12")
    assert rows[0].currency == "BRL"


def test_load_series_does_not_cross_source_and_external_id(repo):
    """(source, external_id) pairs match together, not as independent IN lists."""
    _obs(repo, "myp", "liga_1", D(1), "99")
    rows = load_series(repo, [SeriesKey("liga", "liga_1"), SeriesKey("myp", "myp_1")], days=None)
    assert rows == []


def test_load_series_empty_keys_skips_query(repo):
    statements = _count_obs_selects(repo)
    assert load_series(repo, [], days=30) == []
    assert statements == []


def test_load_series_defaults_today(repo):
    _obs(repo, "liga", "liga_1", date.today(), "10")
    _obs(repo, "liga", "liga_1", date.today() - timedelta(days=40), "9")
    rows = load_series(repo, [SeriesKey("liga", "liga_1")], days=30)
    assert [r.observed_at for r in rows] == [date.today()]


def test_first_real_observation_ignores_snapshots_and_nulls(repo):
    _obs(repo, SNAPSHOT_SOURCE, "liga_1", D(10), "10")
    _obs(repo, "liga", "liga_1", D(8), None)
    _obs(repo, "liga", "liga_1", D(5), "10")
    keys = [SeriesKey("liga", "liga_1"), SeriesKey(SNAPSHOT_SOURCE, "liga_1")]

    assert first_real_observation(repo, keys) == D(5)


def test_first_real_observation_only_snapshot_keys(repo):
    statements = _count_obs_selects(repo)
    assert first_real_observation(repo, [SeriesKey(SNAPSHOT_SOURCE, "liga_1")]) is None
    assert first_real_observation(repo, []) is None
    assert statements == []


def test_first_real_observation_no_rows(repo):
    assert first_real_observation(repo, [SeriesKey("liga", "liga_1")]) is None

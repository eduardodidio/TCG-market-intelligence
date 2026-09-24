"""Tests for src.collection.price_history_keys (F176-T03)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.collection.price_history_keys import (
    BACKFILL_SOURCE,
    SNAPSHOT_SOURCE,
    SOURCE_PRIORITY,
    UNKNOWN_SOURCE_PRIORITY,
    SeriesKey,
    merge_series_by_priority,
    resolve_history_keys,
    source_priority,
)
from src.domain.models import HistoricalPrice

D = date(2026, 9, 24)


def _obs(source, external_id, day=D, price="10.00"):
    return HistoricalPrice(
        source=source,
        external_id=external_id,
        observed_at=day,
        median_price=Decimal(price) if price is not None else None,
    )


def _k(source, external_id):
    return SeriesKey(source, external_id)


# --- constants ---------------------------------------------------------------


def test_snapshot_source_matches_collector_constant():
    from src.collectors.price_snapshot import SNAPSHOT_SOURCE as COLLECTOR_SOURCE

    assert SNAPSHOT_SOURCE == COLLECTOR_SOURCE


def test_backfill_source_matches_collector_constant():
    from src.collectors.price_snapshot import BACKFILL_SOURCE as COLLECTOR_BACKFILL

    assert BACKFILL_SOURCE == COLLECTOR_BACKFILL


def test_source_priority_aligned_with_repository():
    from src.database.repository import Repository

    for source, prio in Repository.SOURCE_PRIORITY.items():
        assert SOURCE_PRIORITY[source] == prio
    assert SOURCE_PRIORITY[SNAPSHOT_SOURCE] == 9


def test_backfill_source_priority_matches_snapshot_priority():
    # ADR 0017 §4: daily_snapshot_backfill resolves like daily_snapshot —
    # same keys, same priority (9), never a "real" point.
    assert SOURCE_PRIORITY[BACKFILL_SOURCE] == SOURCE_PRIORITY[SNAPSHOT_SOURCE] == 9


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("manual", 0),
        ("liga", 1),
        ("jsonld_snapshot", 2),
        ("myp", 3),
        ("foo", UNKNOWN_SOURCE_PRIORITY),
        ("daily_snapshot", 9),
        ("daily_snapshot_backfill", 9),
    ],
)
def test_source_priority(source, expected):
    assert source_priority(source) == expected


def test_series_key_is_hashable_and_frozen():
    key = _k("liga", "liga_1")
    assert {key, _k("liga", "liga_1")} == {key}
    with pytest.raises(AttributeError):
        key.source = "myp"  # type: ignore[misc]


# --- resolve_history_keys ----------------------------------------------------


def test_resolve_normal_happy_path_exact_order():
    keys = resolve_history_keys(7, [("myp", "123")], is_foil=False)
    assert keys == [
        _k("liga", "liga_7"),
        _k("daily_snapshot", "liga_7"),
        _k("manual", "manual_7"),
        _k("daily_snapshot", "manual_7"),
        _k("myp", "123"),
        _k("jsonld_snapshot", "123"),
        _k("daily_snapshot", "123"),
    ]
    assert all(k.external_id != "liga_7_foil" for k in keys)


def test_resolve_foil_happy_path_exact_order():
    keys = resolve_history_keys(7, [("myp", "123")], is_foil=True)
    assert keys == [
        _k("liga", "liga_7_foil"),
        _k("daily_snapshot", "liga_7_foil"),
        _k("manual", "manual_7"),
        _k("daily_snapshot", "manual_7"),
    ]


# card_id_matrix: variant × source_cards
@pytest.mark.parametrize(
    ("source_cards", "is_foil", "must_include", "must_exclude"),
    [
        pytest.param(
            [], False,
            [_k("liga", "liga_7"), _k("daily_snapshot", "liga_7"), _k("manual", "manual_7")],
            [_k("liga", "liga_7_foil")],
            id="no-source-cards-normal",
        ),
        pytest.param(
            [], True,
            [_k("liga", "liga_7_foil"), _k("daily_snapshot", "liga_7_foil"),
             _k("manual", "manual_7")],
            [_k("liga", "liga_7"), _k("daily_snapshot", "liga_7")],
            id="no-source-cards-foil",
        ),
        pytest.param(
            [("myp", "123")], False,
            [_k("myp", "123"), _k("jsonld_snapshot", "123"), _k("daily_snapshot", "123")],
            [_k("liga", "liga_7_foil")],
            id="myp-normal",
        ),
        pytest.param(
            [("myp", "123")], True,
            [_k("liga", "liga_7_foil")],
            [_k("myp", "123"), _k("jsonld_snapshot", "123"), _k("daily_snapshot", "123"),
             _k("liga", "liga_7")],
            id="myp-normal-card-in-foil-variant",
        ),
        pytest.param(
            [("myp", "123_foil")], True,
            [_k("myp", "123_foil"), _k("jsonld_snapshot", "123_foil"),
             _k("daily_snapshot", "123_foil")],
            [_k("liga", "liga_7")],
            id="myp-foil",
        ),
        pytest.param(
            [("myp", "123_foil")], False,
            [_k("liga", "liga_7")],
            [_k("myp", "123_foil"), _k("jsonld_snapshot", "123_foil")],
            id="myp-foil-card-in-normal-variant",
        ),
        pytest.param(
            [("liga", "liga_catalog_M21_123")], False,
            [_k("liga", "liga_catalog_M21_123"),
             _k("jsonld_snapshot", "liga_catalog_M21_123"),
             _k("daily_snapshot", "liga_catalog_M21_123")],
            [],
            id="catalog-normal",
        ),
        pytest.param(
            [("liga", "liga_catalog_M21_123")], True,
            [],
            [_k("liga", "liga_catalog_M21_123")],
            id="catalog-foil",
        ),
    ],
)
def test_resolve_matrix(source_cards, is_foil, must_include, must_exclude):
    keys = resolve_history_keys(7, source_cards, is_foil)
    for key in must_include:
        assert key in keys
    for key in must_exclude:
        assert key not in keys
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize("is_foil", [False, True])
def test_resolve_without_source_cards_keeps_liga_and_manual(is_foil):
    # Regression H1: Liga keys must exist even with no source_cards row.
    keys = resolve_history_keys(1, [], is_foil)
    assert len(keys) == 4
    assert {k.source for k in keys} == {"liga", "manual", "daily_snapshot"}


def test_resolve_deduplicates_source_cards():
    keys = resolve_history_keys(
        7,
        [("myp", "123"), ("myp", "123"), ("liga", "liga_7"), ("jsonld_snapshot", "123")],
        is_foil=False,
    )
    assert len(keys) == len(set(keys))
    assert keys == [
        _k("liga", "liga_7"),
        _k("daily_snapshot", "liga_7"),
        _k("manual", "manual_7"),
        _k("daily_snapshot", "manual_7"),
        _k("myp", "123"),
        _k("jsonld_snapshot", "123"),
        _k("daily_snapshot", "123"),
        _k("jsonld_snapshot", "liga_7"),
    ]


def test_resolve_is_deterministic_and_accepts_iterables():
    sc = [("myp", "b"), ("myp", "a")]
    first = resolve_history_keys(3, iter(sc), is_foil=False)
    assert first == resolve_history_keys(3, tuple(sc), is_foil=False)
    assert [k.external_id for k in first[4:]] == ["b", "b", "b", "a", "a", "a"]


@pytest.mark.parametrize("bad", [0, -1, -999, True, "7", 7.0, None])
def test_resolve_rejects_invalid_card_id(bad):
    with pytest.raises(ValueError):
        resolve_history_keys(bad, [], is_foil=False)


def test_resolve_boundary_card_id_one():
    assert resolve_history_keys(1, [], False)[0] == _k("liga", "liga_1")


# --- merge_series_by_priority ------------------------------------------------


def test_merge_same_day_liga_wins():
    result = merge_series_by_priority([
        _obs("myp", "123", price="40.00"),
        _obs("daily_snapshot", "liga_7", price="45.00"),
        _obs("liga", "liga_7", price="50.00"),
    ])
    assert len(result) == 1
    assert result[0].source == "liga"
    assert result[0].median_price == Decimal("50.00")


def test_merge_manual_beats_liga():
    result = merge_series_by_priority([
        _obs("liga", "liga_7", price="50.00"),
        _obs("manual", "manual_7", price="99.00"),
    ])
    assert [r.source for r in result] == ["manual"]


def test_merge_snapshot_only_day_is_kept():
    result = merge_series_by_priority([
        _obs("liga", "liga_7", day=D - timedelta(days=1)),
        _obs("daily_snapshot", "liga_7", day=D, price="12.00"),
    ])
    assert [(r.observed_at, r.source) for r in result] == [
        (D - timedelta(days=1), "liga"),
        (D, "daily_snapshot"),
    ]


def test_merge_unknown_source_between_myp_and_snapshot():
    assert merge_series_by_priority([
        _obs("foo", "x"), _obs("myp", "123"),
    ])[0].source == "myp"
    assert merge_series_by_priority([
        _obs("daily_snapshot", "x"), _obs("foo", "y"),
    ])[0].source == "foo"


def test_merge_same_day_snapshot_vs_backfill_deterministic_tie():
    # Same-priority tie (both 9) between a real daily_snapshot key and a
    # backfill key landing on the same day for the same variant: must not
    # panic, must pick a deterministic winner by smallest external_id, and
    # both are still "snapshot, not real" regardless of which one wins.
    result = merge_series_by_priority([
        _obs("daily_snapshot", "manual_7", price="10.00"),
        _obs("daily_snapshot_backfill", "liga_7", price="11.00"),
    ])
    assert len(result) == 1
    assert result[0].source == "daily_snapshot_backfill"
    assert result[0].external_id == "liga_7"

    reversed_result = merge_series_by_priority([
        _obs("daily_snapshot_backfill", "liga_7", price="11.00"),
        _obs("daily_snapshot", "manual_7", price="10.00"),
    ])
    assert reversed_result == result


def test_merge_priority_tie_smallest_external_id_wins():
    obs = [_obs("myp", "b", price="2"), _obs("myp", "a", price="1"), _obs("myp", "c")]
    assert merge_series_by_priority(obs)[0].external_id == "a"
    assert merge_series_by_priority(list(reversed(obs)))[0].external_id == "a"


def test_merge_ignores_none_price():
    result = merge_series_by_priority([
        _obs("liga", "liga_7", price=None),
        _obs("myp", "123", price="40.00"),
        _obs("manual", "manual_7", day=D - timedelta(days=1), price=None),
    ])
    assert [(r.observed_at, r.source) for r in result] == [(D, "myp")]


def test_merge_all_none_price_returns_empty():
    assert merge_series_by_priority([_obs("liga", "liga_7", price=None)]) == []


def test_merge_empty():
    assert merge_series_by_priority([]) == []


def test_merge_unordered_input_sorted_asc():
    days = [D, D - timedelta(days=5), D - timedelta(days=2)]
    result = merge_series_by_priority(_obs("liga", "liga_7", day=d) for d in days)
    assert [r.observed_at for r in result] == sorted(days)


def test_merge_single_observation():
    only = _obs("liga", "liga_7")
    assert merge_series_by_priority([only]) == [only]


def test_merge_365_days_one_point_each():
    obs = []
    for i in range(365):
        day = D - timedelta(days=i)
        obs.append(_obs("daily_snapshot", "liga_7", day=day))
        obs.append(_obs("liga", "liga_7", day=day))
    result = merge_series_by_priority(obs)
    assert len(result) == 365
    assert all(r.source == "liga" for r in result)
    assert [r.observed_at for r in result] == sorted({r.observed_at for r in result})

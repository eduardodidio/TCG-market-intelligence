"""Tests for the deck-suggestion queue repository (F172-T03)."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import inspect, update
from sqlalchemy.orm import Session

from src.database.repository import Repository
from src.deck_suggestions import repository as sugg_repo
from src.deck_suggestions.models import DeckSuggestionRequestRow
from src.deck_suggestions.repository import (
    claim_pending,
    colors_from_str,
    colors_to_str,
    count_open_requests,
    create_request,
    delete_pending_request,
    ensure_table,
    get_request,
    list_requests,
    load_result,
    mark_done,
    mark_failed,
    release_for_retry,
    set_saved_deck,
)


@pytest.fixture
def repo():
    return Repository("sqlite:///:memory:")


@pytest.fixture
def engine(repo):
    ensure_table(repo.engine)
    return repo.engine


def _create(engine, user_id="user1", **overrides):
    kwargs = {
        "user_id": user_id,
        "format_name": "commander",
        "commander_card_id": None,
        "commander_name": "Atraxa, Praetors' Voice",
        "colors": "WUBG",
        "archetype": None,
        "notes": None,
    }
    kwargs.update(overrides)
    return create_request(engine, **kwargs)


def _set(engine, request_id, **values):
    with Session(engine) as session:
        session.execute(
            update(DeckSuggestionRequestRow)
            .where(DeckSuggestionRequestRow.id == request_id)
            .values(**values)
        )
        session.commit()


def _fetch(engine, request_id):
    with Session(engine, expire_on_commit=False) as session:
        return session.get(DeckSuggestionRequestRow, request_id)


class TestEnsureTable:
    def test_table_exists(self, engine):
        assert inspect(engine).has_table("deck_suggestion_requests")

    def test_twice_is_noop(self, engine):
        ensure_table(engine)
        ensure_table(engine)
        assert inspect(engine).has_table("deck_suggestion_requests")

    def test_creates_when_missing_and_memoizes(self, repo):
        DeckSuggestionRequestRow.__table__.drop(repo.engine)
        sugg_repo._ensured_engines.discard(id(repo.engine))
        ensure_table(repo.engine)
        assert inspect(repo.engine).has_table("deck_suggestion_requests")
        assert id(repo.engine) in sugg_repo._ensured_engines
        with patch.object(DeckSuggestionRequestRow.__table__, "create") as create:
            ensure_table(repo.engine)
        create.assert_not_called()


class TestColorsHelpers:
    @pytest.mark.parametrize(
        ("colors", "expected"),
        [
            (["U", "W"], "WU"),
            (["g", "r", "b", "u", "w"], "WUBRG"),
            (["B", "B"], "B"),
            (["C"], "C"),
            (["c"], "C"),
            ([], None),
            (None, None),
            (["", " "], None),
            (["X"], None),
        ],
    )
    def test_colors_to_str(self, colors, expected):
        assert colors_to_str(colors) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("WU", ["W", "U"]), ("C", ["C"]), ("", []), (None, [])],
    )
    def test_colors_from_str(self, value, expected):
        assert colors_from_str(value) == expected

    def test_round_trip(self):
        assert colors_from_str(colors_to_str(["R", "W"])) == ["W", "R"]


class TestCreateAndRead:
    def test_create_defaults(self, engine):
        row = _create(engine, notes="Quero proliferar")
        assert row.id is not None
        assert row.status == "pending"
        assert row.attempts == 0
        assert row.created_at is not None
        assert row.notes == "Quero proliferar"
        assert row.result_json is None

    def test_list_newest_first(self, engine):
        a = _create(engine)
        b = _create(engine)
        c = _create(engine)
        _set(engine, a.id, created_at=datetime(2026, 1, 1))
        _set(engine, b.id, created_at=datetime(2026, 1, 3))
        _set(engine, c.id, created_at=datetime(2026, 1, 2))
        assert [r.id for r in list_requests(engine, "user1")] == [b.id, c.id, a.id]

    def test_list_filters_status_and_user(self, engine):
        a = _create(engine)
        _create(engine)
        _create(engine, user_id="other")
        mark_done(engine, a.id, {"ok": True})
        done = list_requests(engine, "user1", status="done")
        assert [r.id for r in done] == [a.id]
        assert len(list_requests(engine, "user1")) == 2
        assert list_requests(engine, "nobody") == []

    def test_list_limit(self, engine):
        for _ in range(5):
            _create(engine)
        assert len(list_requests(engine, "user1", limit=3)) == 3
        assert list_requests(engine, "user1", limit=0) == []

    def test_get_request_ownership(self, engine):
        row = _create(engine)
        got = get_request(engine, row.id, "user1")
        assert got is not None and got.id == row.id
        assert got.commander_name == "Atraxa, Praetors' Voice"
        assert get_request(engine, row.id, "other") is None
        assert get_request(engine, 9999, "user1") is None

    def test_count_open_requests(self, engine):
        pending = _create(engine)
        processing = _create(engine)
        done = _create(engine)
        failed = _create(engine)
        _create(engine, user_id="other")
        _set(engine, processing.id, status="processing")
        mark_done(engine, done.id, {})
        mark_failed(engine, failed.id, "boom")
        assert pending.status == "pending"
        assert count_open_requests(engine, "user1") == 2
        assert count_open_requests(engine, "nobody") == 0


class TestDeletePending:
    def test_deletes_pending(self, engine):
        row = _create(engine)
        assert delete_pending_request(engine, row.id, "user1") is True
        assert get_request(engine, row.id, "user1") is None

    def test_other_user_cannot_delete(self, engine):
        row = _create(engine)
        assert delete_pending_request(engine, row.id, "other") is False
        assert get_request(engine, row.id, "user1") is not None

    def test_processing_not_deleted(self, engine):
        row = _create(engine)
        claim_pending(engine, 1)
        assert delete_pending_request(engine, row.id, "user1") is False

    def test_missing_id(self, engine):
        assert delete_pending_request(engine, 12345, "user1") is False


class TestClaimPending:
    def test_happy_flow(self, engine):
        row = _create(engine)
        now = datetime(2026, 9, 25, 3, 0, 0)
        claimed = claim_pending(engine, 5, now=now)
        assert [r.id for r in claimed] == [row.id]
        assert claimed[0].status == "processing"
        assert claimed[0].attempts == 1
        assert claimed[0].started_at == now

        result = {"deck_name": "Atraxa Superfriends", "strategy": "Proliferar contadores — ação"}
        mark_done(engine, row.id, result)
        done = get_request(engine, row.id, "user1")
        assert done.status == "done"
        assert done.processed_at is not None
        assert done.error_message is None
        assert "ação" in done.result_json  # ensure_ascii=False
        assert load_result(done) == result

    def test_limit_zero(self, engine):
        _create(engine)
        assert claim_pending(engine, 0) == []
        assert claim_pending(engine, -1) == []

    def test_no_candidates(self, engine):
        assert claim_pending(engine, 5) == []

    def test_sequential_claims_never_return_same_row(self, engine):
        a = _create(engine)
        b = _create(engine)
        first = claim_pending(engine, 1)
        second = claim_pending(engine, 1)
        third = claim_pending(engine, 1)
        assert [r.id for r in first] == [a.id]
        assert [r.id for r in second] == [b.id]
        assert third == []

    def test_ordered_by_created_at_and_limited(self, engine):
        a = _create(engine)
        b = _create(engine)
        c = _create(engine)
        _set(engine, a.id, created_at=datetime(2026, 1, 3))
        _set(engine, b.id, created_at=datetime(2026, 1, 1))
        _set(engine, c.id, created_at=datetime(2026, 1, 2))
        claimed = claim_pending(engine, 2)
        assert [r.id for r in claimed] == [b.id, c.id]

    def test_skips_done_and_failed(self, engine):
        a = _create(engine)
        b = _create(engine)
        mark_done(engine, a.id, {})
        mark_failed(engine, b.id, "x")
        assert claim_pending(engine, 5) == []

    def test_stale_threshold_boundary(self, engine):
        now = datetime(2026, 9, 25, 3, 0, 0)
        stale_after = timedelta(hours=2)
        at_threshold = _create(engine)
        past_threshold = _create(engine)
        fresh = _create(engine)
        _set(engine, at_threshold.id, status="processing", attempts=1,
             started_at=now - stale_after)
        _set(engine, past_threshold.id, status="processing", attempts=1,
             started_at=now - stale_after - timedelta(seconds=1))
        _set(engine, fresh.id, status="processing", attempts=1,
             started_at=now - timedelta(minutes=5))
        claimed = claim_pending(engine, 10, stale_after=stale_after, now=now)
        assert [r.id for r in claimed] == [past_threshold.id]
        assert claimed[0].attempts == 2
        assert claimed[0].started_at == now

    def test_processing_without_started_at_not_reclaimed(self, engine):
        row = _create(engine)
        _set(engine, row.id, status="processing", started_at=None)
        assert claim_pending(engine, 5) == []

    def test_concurrent_status_change_not_returned(self, engine):
        row = _create(engine)
        other = _create(engine)
        real_select = sugg_repo._select_candidates

        def racing_select(session, limit, cutoff):
            candidates = real_select(session, limit, cutoff)
            # Another runner claims ``row`` between our SELECT and UPDATE
            _set(engine, row.id, status="processing", started_at=datetime.now(), attempts=1)
            return candidates

        with patch.object(sugg_repo, "_select_candidates", side_effect=racing_select):
            claimed = claim_pending(engine, 5)
        assert [r.id for r in claimed] == [other.id]
        assert _fetch(engine, row.id).attempts == 1

    def test_concurrent_stale_reclaim_not_returned(self, engine):
        now = datetime(2026, 9, 25, 3, 0, 0)
        row = _create(engine)
        _set(engine, row.id, status="processing", attempts=1,
             started_at=now - timedelta(hours=5))
        real_select = sugg_repo._select_candidates

        def racing_select(session, limit, cutoff):
            candidates = real_select(session, limit, cutoff)
            # Another runner re-claims the stale row first (new started_at)
            _set(engine, row.id, started_at=now - timedelta(minutes=1), attempts=2)
            return candidates

        with patch.object(sugg_repo, "_select_candidates", side_effect=racing_select):
            claimed = claim_pending(engine, 5, now=now)
        assert claimed == []
        assert _fetch(engine, row.id).attempts == 2


class TestMarkFailedAndRetry:
    def test_mark_failed_truncates(self, engine):
        row = _create(engine)
        mark_failed(engine, row.id, "e" * 1500)
        got = get_request(engine, row.id, "user1")
        assert got.status == "failed"
        assert len(got.error_message) == 1000
        assert got.processed_at is not None

    def test_mark_failed_short_and_empty(self, engine):
        row = _create(engine)
        mark_failed(engine, row.id, "")
        assert get_request(engine, row.id, "user1").error_message == ""
        mark_failed(engine, row.id, "x" * 1000)
        assert len(get_request(engine, row.id, "user1").error_message) == 1000

    def test_release_for_retry_keeps_attempts(self, engine):
        row = _create(engine)
        claim_pending(engine, 1)
        release_for_retry(engine, row.id, "rate limited")
        got = get_request(engine, row.id, "user1")
        assert got.status == "pending"
        assert got.attempts == 1
        assert got.error_message == "rate limited"
        reclaimed = claim_pending(engine, 1)
        assert reclaimed[0].attempts == 2

    def test_mark_done_clears_error(self, engine):
        row = _create(engine)
        release_for_retry(engine, row.id, "timeout")
        mark_done(engine, row.id, {"deck_name": "X"})
        assert get_request(engine, row.id, "user1").error_message is None


class TestSetSavedDeck:
    def test_links_deck(self, repo, engine):
        row = _create(engine)
        deck = repo.create_deck("user1", "Atraxa")
        set_saved_deck(engine, row.id, deck.id)
        assert get_request(engine, row.id, "user1").saved_deck_id == deck.id


class TestLoadResult:
    def test_none_when_missing(self, engine):
        assert load_result(_create(engine)) is None

    def test_corrupt_json(self):
        assert load_result(DeckSuggestionRequestRow(result_json="{not json")) is None

    def test_non_dict_json(self):
        assert load_result(DeckSuggestionRequestRow(result_json="[1, 2]")) is None

    def test_unicode_round_trip(self, engine):
        row = _create(engine)
        payload = {"unresolved": ["Nome Inventado"], "strategy": "Controle — ç ã é", "n": 1.5}
        mark_done(engine, row.id, payload)
        assert load_result(get_request(engine, row.id, "user1")) == payload

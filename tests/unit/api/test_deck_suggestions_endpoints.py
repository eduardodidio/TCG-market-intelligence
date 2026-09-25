"""Tests for the deck-suggestions API router (F172-T08)."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.deck_suggestions import _cards_for_deck, router
from src.api.schemas.deck_suggestions import to_schema
from src.database.models import CardRow
from src.database.repository import Repository
from src.deck_suggestions import repository as sugg_repo
from src.deck_suggestions.models import DeckSuggestionRequestRow

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path):
    # File-backed DB: TestClient runs sync endpoints in worker threads, and
    # an in-memory SQLite database is per-connection.
    r = Repository(f"sqlite:///{tmp_path / 'sugg.db'}")
    sugg_repo._ensured_engines.discard(id(r.engine))
    sugg_repo.ensure_table(r.engine)
    return r


def _client(repo, user_id="user1") -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    return TestClient(app)


@pytest.fixture
def client(repo):
    return _client(repo)


def _add_card(
    repo,
    name="Atraxa, Praetors' Voice",
    type_line="Legendary Creature — Phyrexian Angel Horror",
    ci="WUBG",
    **kw,
):
    with Session(repo.engine, expire_on_commit=False) as s:
        card = CardRow(
            game="mtg",
            name_en=name,
            type_line=type_line,
            color_identity=ci,
            set_code=kw.get("set_code", "cm2"),
            collector_number=kw.get("collector_number", "10"),
        )
        s.add(card)
        s.commit()
        return card


def _create_row(repo, user_id="user1", status="pending", **overrides):
    kwargs = {
        "user_id": user_id,
        "format_name": "modern",
        "commander_card_id": None,
        "commander_name": None,
        "colors": "RG",
        "archetype": "aggro",
        "notes": None,
    }
    kwargs.update(overrides)
    row = sugg_repo.create_request(repo.engine, **kwargs)
    if status != "pending":
        with Session(repo.engine) as s:
            s.execute(
                update(DeckSuggestionRequestRow)
                .where(DeckSuggestionRequestRow.id == row.id)
                .values(status=status)
            )
            s.commit()
    return row


def _result(**overrides):
    data = {
        "deck_name": "Atraxa Superfriends",
        "strategy": "Proliferar.",
        "format_name": "commander",
        "commander": {"name_en": "Atraxa, Praetors' Voice", "card_id": None},
        "cards": [
            {
                "name_en": "Sol Ring",
                "quantity": 1,
                "card_id": None,
                "set_code": "cmr",
                "collector_number": "472",
            },
            {"name_en": "Forest", "quantity": 30, "card_id": None},
            {"name_en": "Nome Inventado", "quantity": "x", "card_id": None},
        ],
        "summary": {
            "total_cards": 32,
            "owned_cards": 20,
            "missing_cards": 12,
            "missing_cost_brl": 842.3,
            "unresolved_count": 1,
        },
        "unresolved": ["Nome Inventado"],
    }
    data.update(overrides)
    return data


def _done_row(repo, user_id="user1", result=None):
    row = _create_row(repo, user_id=user_id)
    sugg_repo.mark_done(repo.engine, row.id, result if result is not None else _result())
    return row


def _modern_body(**overrides):
    body = {"format_name": "modern", "colors": ["R", "G"], "archetype": "aggro"}
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# POST /deck-suggestions
# ---------------------------------------------------------------------------


class TestCreateSuggestion:
    def test_commander_request_derives_colors_from_card(self, client, repo):
        card = _add_card(repo)
        resp = client.post(
            "/deck-suggestions",
            json={
                "format_name": "Commander",
                "commander_card_id": card.id,
                "colors": ["R"],
                "notes": " superfriends ",
            },
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["status"] == "pending"
        assert data["format_name"] == "commander"
        assert data["colors"] == ["W", "U", "B", "G"]
        assert data["commander_card_id"] == card.id
        assert data["commander_name"] == "Atraxa, Praetors' Voice"
        assert data["notes"] == "superfriends"
        assert data["archetype"] is None
        assert data["summary"] is None and data["result"] is None

    def test_commander_with_optional_archetype(self, client, repo):
        card = _add_card(repo)
        resp = client.post(
            "/deck-suggestions",
            json={"format_name": "commander", "commander_card_id": card.id, "archetype": " Combo "},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["archetype"] == "combo"

    def test_colorless_commander(self, client, repo):
        card = _add_card(repo, name="Kozilek", type_line="Legendary Creature — Eldrazi", ci="")
        resp = client.post(
            "/deck-suggestions", json={"format_name": "commander", "commander_card_id": card.id}
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["colors"] == ["C"]

    def test_modern_colors_normalized(self, client):
        resp = client.post(
            "/deck-suggestions", json=_modern_body(colors=["r", "R", "g"], commander_card_id=99)
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["colors"] == ["R", "G"]
        assert data["archetype"] == "aggro"
        assert data["commander_card_id"] is None

    def test_colors_stored_in_wubrg_order(self, client):
        resp = client.post("/deck-suggestions", json=_modern_body(colors=["G", "W", "U"]))
        assert resp.json()["data"]["colors"] == ["W", "U", "G"]

    def test_colorless_non_commander(self, client):
        resp = client.post("/deck-suggestions", json=_modern_body(colors=["c"]))
        assert resp.status_code == 201
        assert resp.json()["data"]["colors"] == ["C"]

    def test_blank_notes_become_none(self, client):
        resp = client.post("/deck-suggestions", json=_modern_body(notes="   "))
        assert resp.status_code == 201
        assert resp.json()["data"]["notes"] is None

    def test_notes_1000_chars_accepted(self, client):
        resp = client.post("/deck-suggestions", json=_modern_body(notes="a" * 1000))
        assert resp.status_code == 201

    def test_notes_1001_chars_rejected(self, client):
        resp = client.post("/deck-suggestions", json=_modern_body(notes="a" * 1001))
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "body, fragment",
        [
            ({"format_name": "brawl", "colors": ["R"], "archetype": "aggro"}, "Unknown format"),
            ({"format_name": "commander"}, "commander_card_id is required"),
            ({"format_name": "commander", "commander_card_id": 9999}, "not found"),
            ({"format_name": "modern", "archetype": "aggro"}, "colors must be"),
            ({"format_name": "modern", "colors": ["  "], "archetype": "aggro"}, "colors must be"),
            ({"format_name": "modern", "colors": ["X"], "archetype": "aggro"}, "colors must be"),
            (
                {"format_name": "modern", "colors": ["C", "W"], "archetype": "aggro"},
                "colors must be",
            ),
            ({"format_name": "modern", "colors": ["R"]}, "archetype is required"),
            ({"format_name": "modern", "colors": ["R"], "archetype": "foo"}, "Unknown archetype"),
        ],
    )
    def test_validation_errors(self, client, body, fragment):
        resp = client.post("/deck-suggestions", json=body)
        assert resp.status_code == 400
        assert fragment in resp.json()["detail"]["message"]
        assert resp.json()["detail"]["code"] == "VALIDATION_ERROR"

    def test_non_legendary_commander_rejected(self, client, repo):
        card = _add_card(repo, name="Grizzly Bears", type_line="Creature — Bear", ci="G")
        resp = client.post(
            "/deck-suggestions", json={"format_name": "commander", "commander_card_id": card.id}
        )
        assert resp.status_code == 400
        assert "not a Legendary Creature" in resp.json()["detail"]["message"]

    def test_sixth_open_request_rejected(self, client, repo):
        for _ in range(3):
            _create_row(repo)
        for _ in range(2):
            _create_row(repo, status="processing")
        _create_row(repo, status="done")
        _create_row(repo, status="failed")
        _create_row(repo, user_id="other")
        resp = client.post("/deck-suggestions", json=_modern_body())
        assert resp.status_code == 429
        assert resp.json()["detail"]["code"] == "VALIDATION_LIMIT_EXCEEDED"

    def test_fifth_open_request_allowed(self, client, repo):
        for _ in range(4):
            _create_row(repo)
        _create_row(repo, status="done")
        _create_row(repo, status="failed")
        resp = client.post("/deck-suggestions", json=_modern_body())
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# GET /deck-suggestions
# ---------------------------------------------------------------------------


class TestListSuggestions:
    def test_newest_first_with_summary(self, client, repo):
        first = _create_row(repo)
        done = _done_row(repo)
        _create_row(repo, user_id="other")
        resp = client.get("/deck-suggestions")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert [d["id"] for d in data] == [done.id, first.id]
        assert data[0]["summary"]["missing_cost_brl"] == 842.3
        assert data[0]["result"] is None
        assert data[1]["summary"] is None

    def test_status_filter(self, client, repo):
        _create_row(repo)
        done = _done_row(repo)
        resp = client.get("/deck-suggestions?status=done")
        assert [d["id"] for d in resp.json()["data"]] == [done.id]

    def test_invalid_status(self, client):
        resp = client.get("/deck-suggestions?status=weird")
        assert resp.status_code == 400
        assert "Invalid status" in resp.json()["detail"]["message"]

    @pytest.mark.parametrize("limit, expected", [(1, 200), (50, 200), (0, 422), (51, 422)])
    def test_limit_bounds(self, client, limit, expected):
        assert client.get(f"/deck-suggestions?limit={limit}").status_code == expected

    def test_limit_applied(self, client, repo):
        for _ in range(3):
            _create_row(repo)
        assert len(client.get("/deck-suggestions?limit=2").json()["data"]) == 2


# ---------------------------------------------------------------------------
# GET /deck-suggestions/{id}
# ---------------------------------------------------------------------------


class TestGetSuggestion:
    def test_get_with_result(self, client, repo):
        row = _done_row(repo)
        resp = client.get(f"/deck-suggestions/{row.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "done"
        assert data["result"]["deck_name"] == "Atraxa Superfriends"
        assert data["summary"]["total_cards"] == 32
        assert data["processed_at"] is not None

    def test_pending_has_no_result(self, client, repo):
        row = _create_row(repo)
        data = client.get(f"/deck-suggestions/{row.id}").json()["data"]
        assert data["result"] is None and data["summary"] is None

    def test_other_users_request_is_404(self, repo):
        row = _create_row(repo, user_id="other")
        resp = _client(repo).get(f"/deck-suggestions/{row.id}")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "RESOURCE_NOT_FOUND"

    def test_missing_is_404(self, client):
        assert client.get("/deck-suggestions/12345").status_code == 404


# ---------------------------------------------------------------------------
# POST /deck-suggestions/{id}/save
# ---------------------------------------------------------------------------


class TestSaveSuggestion:
    def test_save_creates_deck_with_commander(self, client, repo):
        row = _done_row(repo)
        resp = client.post(f"/deck-suggestions/{row.id}/save")
        assert resp.status_code == 200
        deck_id = resp.json()["data"]["deck_id"]
        deck = repo.get_deck(deck_id)
        assert deck.name == "Atraxa Superfriends"
        assert deck.user_id == "user1"
        cards = {c.name_en: c for c in repo.get_deck_cards(deck_id)}
        assert set(cards) == {"Atraxa, Praetors' Voice", "Sol Ring", "Forest", "Nome Inventado"}
        assert cards["Forest"].quantity == 30
        assert cards["Nome Inventado"].quantity == 1
        assert cards["Nome Inventado"].card_id is None
        assert cards["Sol Ring"].set_code == "cmr"
        assert sugg_repo.get_request(repo.engine, row.id, "user1").saved_deck_id == deck_id

    def test_save_with_custom_name(self, client, repo):
        row = _done_row(repo)
        resp = client.post(f"/deck-suggestions/{row.id}/save", json={"deck_name": " Meu deck "})
        assert repo.get_deck(resp.json()["data"]["deck_id"]).name == "Meu deck"

    def test_save_default_name_when_result_has_none(self, client, repo):
        row = _done_row(repo, result=_result(deck_name=None, commander=None))
        resp = client.post(f"/deck-suggestions/{row.id}/save", json={})
        deck_id = resp.json()["data"]["deck_id"]
        assert repo.get_deck(deck_id).name == f"Deck suggestion #{row.id}"
        assert len(repo.get_deck_cards(deck_id)) == 3

    def test_save_is_idempotent(self, client, repo):
        row = _done_row(repo)
        first = client.post(f"/deck-suggestions/{row.id}/save").json()["data"]["deck_id"]
        second = client.post(f"/deck-suggestions/{row.id}/save").json()["data"]["deck_id"]
        assert first == second
        assert len(repo.list_decks("user1")) == 1

    def test_save_recreates_when_saved_deck_was_deleted(self, client, repo):
        row = _done_row(repo)
        first = client.post(f"/deck-suggestions/{row.id}/save").json()["data"]["deck_id"]
        repo.delete_deck(first, "user1")
        second = client.post(f"/deck-suggestions/{row.id}/save").json()["data"]["deck_id"]
        # SQLite may reuse the deleted id; what matters is a live deck exists again.
        assert repo.get_deck(second) is not None
        assert len(repo.list_decks("user1")) == 1
        assert len(repo.get_deck_cards(second)) == 4

    def test_save_pending_is_409(self, client, repo):
        row = _create_row(repo)
        resp = client.post(f"/deck-suggestions/{row.id}/save")
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "RESOURCE_CONFLICT"

    def test_save_corrupt_result_is_409(self, client, repo):
        row = _done_row(repo)
        with Session(repo.engine) as s:
            s.execute(
                update(DeckSuggestionRequestRow)
                .where(DeckSuggestionRequestRow.id == row.id)
                .values(result_json="{not json")
            )
            s.commit()
        assert client.post(f"/deck-suggestions/{row.id}/save").status_code == 409

    def test_save_other_users_request_is_404(self, repo):
        row = _done_row(repo, user_id="other")
        assert _client(repo).post(f"/deck-suggestions/{row.id}/save").status_code == 404

    def test_deck_name_boundaries(self, client, repo):
        row = _done_row(repo)
        assert (
            client.post(
                f"/deck-suggestions/{row.id}/save", json={"deck_name": "a" * 301}
            ).status_code
            == 422
        )
        assert (
            client.post(f"/deck-suggestions/{row.id}/save", json={"deck_name": ""}).status_code
            == 422
        )
        resp = client.post(f"/deck-suggestions/{row.id}/save", json={"deck_name": "a" * 300})
        assert resp.status_code == 200
        assert repo.get_deck(resp.json()["data"]["deck_id"]).name == "a" * 300


# ---------------------------------------------------------------------------
# DELETE /deck-suggestions/{id}
# ---------------------------------------------------------------------------


class TestDeleteSuggestion:
    def test_delete_pending(self, client, repo):
        row = _create_row(repo)
        resp = client.delete(f"/deck-suggestions/{row.id}")
        assert resp.status_code == 204
        assert sugg_repo.get_request(repo.engine, row.id, "user1") is None

    @pytest.mark.parametrize("status", ["processing", "done", "failed"])
    def test_delete_non_pending_is_409(self, client, repo, status):
        row = _create_row(repo, status=status)
        resp = client.delete(f"/deck-suggestions/{row.id}")
        assert resp.status_code == 409
        assert sugg_repo.get_request(repo.engine, row.id, "user1") is not None

    def test_delete_other_users_request_is_404(self, repo):
        row = _create_row(repo, user_id="other")
        assert _client(repo).delete(f"/deck-suggestions/{row.id}").status_code == 404
        assert sugg_repo.get_request(repo.engine, row.id, "other") is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_cards_for_deck_skips_invalid_entries_and_dedupes_commander(self):
        cards = _cards_for_deck(
            {
                "commander": {"name_en": "Atraxa", "card_id": 1, "set_code": "cm2"},
                "cards": [
                    "garbage",
                    {"quantity": 1},
                    {"name_en": "atraxa", "quantity": 1},
                    {"name_en": "Sol Ring", "quantity": 0, "card_id": 2},
                ],
            }
        )
        assert cards == [
            {
                "name_en": "Atraxa",
                "set_code": "cm2",
                "collector_number": None,
                "quantity": 1,
                "card_id": 1,
            },
            {
                "name_en": "Sol Ring",
                "set_code": None,
                "collector_number": None,
                "quantity": 1,
                "card_id": 2,
            },
        ]

    def test_cards_for_deck_empty_result(self):
        assert _cards_for_deck({}) == []

    def _row(self, **kw):
        base = dict(
            id=1,
            format_name="modern",
            commander_card_id=None,
            commander_name=None,
            colors="RG",
            archetype="aggro",
            notes=None,
            status="done",
            error_message=None,
            saved_deck_id=None,
            created_at=datetime(2026, 9, 24),
            processed_at=None,
            result_json=None,
        )
        base.update(kw)
        return SimpleNamespace(**base)

    def test_to_schema_invalid_summary_is_none(self):
        row = self._row(result_json='{"summary": {"total_cards": "many"}}')
        schema = to_schema(row, include_result=True)
        assert schema.summary is None
        assert schema.result == {"summary": {"total_cards": "many"}}

    def test_to_schema_summary_not_dict(self):
        row = self._row(result_json='{"summary": 3}')
        assert to_schema(row, include_result=False).summary is None

    def test_to_schema_ignores_result_when_not_done(self):
        row = self._row(status="failed", error_message="boom", result_json='{"summary": {}}')
        schema = to_schema(row, include_result=True)
        assert schema.result is None and schema.error_message == "boom"

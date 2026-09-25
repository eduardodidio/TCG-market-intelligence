"""Tests for the deck-suggestion processor (F172-T09)."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import update
from sqlalchemy.orm import Session

from src.database.models import CardRow, PriceObservationRow, UserCollectionRow
from src.database.repository import Repository
from src.deck_suggestions import processor
from src.deck_suggestions.claude_runner import ClaudeRunnerError
from src.deck_suggestions.models import DeckSuggestionRequestRow
from src.deck_suggestions.processor import (
    OwnedCollection,
    ProcessSummary,
    enrich,
    load_owned_cards,
    process_pending_suggestions,
    resolve_cards,
)
from src.deck_suggestions.prompt import OwnedCard, ParsedCard, ParsedSuggestion
from src.deck_suggestions.repository import create_request, ensure_table, get_request

USER = "user1"
RESULT_KEYS = {
    "deck_name", "strategy", "format_name", "commander", "cards", "summary",
    "unresolved", "warnings", "provider", "model", "generated_at",
}
CARD_KEYS = {
    "name_en", "quantity", "category", "reason", "card_id", "set_code",
    "collector_number", "image_uri", "is_owned", "owned_quantity",
    "missing_quantity", "unit_price", "missing_cost",
}
SUMMARY_KEYS = {
    "total_cards", "owned_cards", "missing_cards", "missing_cost_brl", "unresolved_count",
}


# --------------------------------------------------------------------------- fixtures


class FakeRunner:
    provider = "fake"
    model = "m"

    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.prompts: list[str] = []

    def run(self, prompt: str) -> str:
        self.prompts.append(prompt)
        item = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(item, Exception):
            raise item
        return item


def _reply(cards, deck_name="Deck Teste", strategy="Estratégia"):
    return json.dumps(
        {
            "deck_name": deck_name,
            "strategy": strategy,
            "cards": [
                {"name": n, "quantity": q, "category": "Cat", "reason": "Motivo"}
                for n, q in cards
            ],
        }
    )


@pytest.fixture
def repo():
    r = Repository("sqlite:///:memory:")
    ensure_table(r.engine)
    return r


_NUM = 0


def _card(repo, name_en, *, name_pt=None, identity="", type_line="Artifact",
          image="https://img/x.jpg", set_code="cmr", number=None):
    global _NUM
    _NUM += 1
    number = number or str(_NUM)
    with Session(repo.engine) as s:
        row = CardRow(
            game="magic", name_en=name_en, name_pt=name_pt, color_identity=identity,
            type_line=type_line, image_uri=image, set_code=set_code, collector_number=number,
        )
        s.add(row)
        s.commit()
        return row.id


def _own(repo, card_id, qty, *, name_en=None, name_pt=None, user=USER):
    with Session(repo.engine) as s:
        s.add(UserCollectionRow(
            user_id=user, card_id=card_id, set_code="cmr", collector_number="1",
            name_en=name_en, name_pt=name_pt, quantity=qty,
        ))
        s.commit()


def _price(repo, card_id, value):
    with Session(repo.engine) as s:
        s.add(PriceObservationRow(
            source="liga", external_id=f"liga_{card_id}", observed_at=date.today(),
            median_price=Decimal(str(value)), currency="BRL",
        ))
        s.commit()


def _request(repo, *, fmt="commander", commander=None, commander_id=None, colors="WUBG",
             archetype=None, user=USER):
    return create_request(
        repo.engine, user_id=user, format_name=fmt, commander_card_id=commander_id,
        commander_name=commander, colors=colors, archetype=archetype, notes="gosto de +1/+1",
    )


def _status(repo, request_id, user=USER):
    return get_request(repo.engine, request_id, user)


def _result(repo, request_id):
    return json.loads(_status(repo, request_id).result_json)


def _set_created(repo, request_id, when):
    with Session(repo.engine) as s:
        s.execute(update(DeckSuggestionRequestRow)
                  .where(DeckSuggestionRequestRow.id == request_id).values(created_at=when))
        s.commit()


def _sample_owned_cards():
    return [
        OwnedCard("Sol Ring", None, 2, "", "Artifact", 12.5),
        OwnedCard("Swords to Plowshares", None, 1, "W", "Instant", 8.0),
    ]


# --------------------------------------------------------------------------- happy path


def test_commander_request_happy_path(repo):
    cmd = _card(repo, "Atraxa, Praetors' Voice", identity="WUBG", type_line="Legendary Creature")
    ids = {n: _card(repo, n) for n in ["Sol Ring", "Arcane Signet", "Command Tower",
                                        "Cyclonic Rift", "Smothering Tithe"]}
    for n in ["Sol Ring", "Arcane Signet", "Command Tower"]:
        _own(repo, ids[n], 1)
    _own(repo, cmd, 1)
    _price(repo, ids["Cyclonic Rift"], "30.10")
    _price(repo, ids["Smothering Tithe"], "90.25")
    _price(repo, ids["Sol Ring"], "12.5")
    req = _request(repo, commander="Atraxa, Praetors' Voice", commander_id=cmd)
    runner = FakeRunner([_reply([(n, 1) for n in ids])])

    summary = process_pending_suggestions(repo, runner)

    assert summary == ProcessSummary(total=1, done=1)
    row = _status(repo, req.id)
    assert row.status == "done" and row.error_message is None
    result = _result(repo, req.id)
    assert set(result) == RESULT_KEYS
    assert set(result["summary"]) == SUMMARY_KEYS
    assert all(set(c) == CARD_KEYS for c in result["cards"])
    assert result["commander"]["name_en"] == "Atraxa, Praetors' Voice"
    assert result["commander"]["card_id"] == cmd
    assert result["provider"] == "fake" and result["model"] == "m"
    assert result["format_name"] == "commander"
    datetime.fromisoformat(result["generated_at"])
    s = result["summary"]
    assert s["total_cards"] == 6  # 5 cards + commander
    assert s["owned_cards"] == 4  # 3 cards + commander
    assert s["missing_cards"] == 2
    assert s["missing_cost_brl"] == pytest.approx(120.35)
    assert s["unresolved_count"] == 0
    by_name = {c["name_en"]: c for c in result["cards"]}
    assert by_name["Sol Ring"]["is_owned"] and by_name["Sol Ring"]["owned_quantity"] == 1
    assert by_name["Sol Ring"]["unit_price"] == 12.5 and by_name["Sol Ring"]["missing_cost"] == 0.0
    assert by_name["Cyclonic Rift"]["missing_cost"] == 30.1
    assert not by_name["Cyclonic Rift"]["is_owned"]
    # prompt lists the owned cards; not logged or stored
    assert "1x Sol Ring" in runner.prompts[0]
    assert "<observacoes_do_usuario>" in runner.prompts[0]


def test_modern_partial_ownership_and_basic_land(repo):
    bolt = _card(repo, "Lightning Bolt", identity="R")
    _card(repo, "Mountain", identity="", type_line="Basic Land — Mountain")
    _own(repo, bolt, 1)
    _price(repo, bolt, "5")
    req = _request(repo, fmt="modern", colors="R", archetype="aggro")
    runner = FakeRunner([_reply([("Lightning Bolt", 4), ("Mountain", 20)])])
    process_pending_suggestions(repo, runner)

    result = _result(repo, req.id)
    cards = {c["name_en"]: c for c in result["cards"]}
    assert cards["Lightning Bolt"]["owned_quantity"] == 1
    assert cards["Lightning Bolt"]["missing_quantity"] == 3
    assert cards["Lightning Bolt"]["missing_cost"] == 15.0
    assert not cards["Lightning Bolt"]["is_owned"]
    mountain = cards["Mountain"]
    assert mountain["is_owned"] and mountain["missing_quantity"] == 0
    assert mountain["unit_price"] == 0.0 and mountain["missing_cost"] == 0.0
    assert result["summary"]["missing_cards"] == 3
    assert result["summary"]["missing_cost_brl"] == 15.0
    assert result["commander"] is None


def test_pt_name_and_dfc_front_face_resolve(repo):
    swords = _card(repo, "Swords to Plowshares", name_pt="Espadas em Arados", identity="W")
    delver = _card(repo, "Delver of Secrets // Insectile Aberration", identity="U")
    req = _request(repo, fmt="modern", colors="WU", archetype="tempo")
    process_pending_suggestions(
        repo, FakeRunner([_reply([("Espadas em Arados", 1), ("Delver of Secrets", 4)])])
    )
    cards = {c["card_id"]: c for c in _result(repo, req.id)["cards"]}
    assert cards[swords]["name_en"] == "Swords to Plowshares"
    assert cards[delver]["name_en"] == "Delver of Secrets // Insectile Aberration"


def test_empty_collection_prompt_still_works(repo):
    _card(repo, "Sol Ring")
    req = _request(repo, fmt="modern", colors="C", archetype="ramp")
    runner = FakeRunner([_reply([("Sol Ring", 1)])])
    process_pending_suggestions(repo, runner)
    assert "(nenhuma carta compatível na coleção)" in runner.prompts[0]
    assert _status(repo, req.id).status == "done"
    assert _result(repo, req.id)["summary"]["missing_cost_brl"] is None


def test_unknown_names_are_unresolved(repo):
    ring = _card(repo, "Sol Ring")
    _price(repo, ring, "10")
    req = _request(repo, fmt="modern", colors="C", archetype="ramp")
    runner = FakeRunner([_reply([("Sol Ring", 1), ("Nome Inventado", 2)])])
    process_pending_suggestions(repo, runner)
    result = _result(repo, req.id)
    assert result["unresolved"] == ["Nome Inventado"]
    fake = next(c for c in result["cards"] if c["name_en"] == "Nome Inventado")
    assert fake["card_id"] is None and fake["unit_price"] is None and fake["missing_cost"] is None
    assert result["summary"]["unresolved_count"] == 1
    assert result["summary"]["missing_cost_brl"] == 10.0


def test_all_unresolved_done_with_none_cost_and_warning(repo):
    req = _request(repo, fmt="modern", colors="R", archetype="aggro")
    process_pending_suggestions(repo, FakeRunner([_reply([("Foo", 4), ("Bar", 4)])]))
    row = _status(repo, req.id)
    assert row.status == "done"
    result = _result(repo, req.id)
    assert result["summary"]["missing_cost_brl"] is None
    assert result["summary"]["unresolved_count"] == 2
    assert any("Nenhum preço" in w for w in result["warnings"])
    assert any("não encontradas" in w for w in result["warnings"])


def test_commander_listed_in_cards_is_removed(repo):
    cmd = _card(repo, "Atraxa, Praetors' Voice", identity="WUBG")
    req = _request(repo, commander="Atraxa, Praetors' Voice", commander_id=cmd)
    process_pending_suggestions(
        repo, FakeRunner([_reply([("Atraxa, Praetors' Voice", 1), ("Forest", 10)])])
    )
    result = _result(repo, req.id)
    assert [c["name_en"] for c in result["cards"]] == ["Forest"]
    assert result["summary"]["total_cards"] == 11
    assert any("removido" in w for w in result["warnings"])


def test_commander_resolved_by_name_when_card_id_missing(repo):
    cmd = _card(repo, "Krenko, Mob Boss", identity="R")
    req = _request(repo, commander="Krenko, Mob Boss", commander_id=None, colors="R")
    process_pending_suggestions(repo, FakeRunner([_reply([("Mountain", 99)])]))
    assert _result(repo, req.id)["commander"]["card_id"] == cmd


# --------------------------------------------------------------------------- errors


def test_transient_error_retries_then_fails_on_third_attempt(repo):
    req = _request(repo, fmt="modern", colors="R", archetype="aggro")
    runner = FakeRunner([ClaudeRunnerError("timeout", transient=True)])

    s1 = process_pending_suggestions(repo, runner)
    assert s1 == ProcessSummary(total=1, retried=1)
    row = _status(repo, req.id)
    assert row.status == "pending" and row.attempts == 1 and row.error_message == "timeout"

    process_pending_suggestions(repo, runner)
    assert _status(repo, req.id).status == "pending"

    s3 = process_pending_suggestions(repo, runner)
    assert s3 == ProcessSummary(total=1, failed=1)
    row = _status(repo, req.id)
    assert row.status == "failed" and row.attempts == 3


def test_non_transient_error_fails_immediately(repo):
    req = _request(repo, fmt="modern", colors="R", archetype="aggro")
    s = process_pending_suggestions(
        repo, FakeRunner([ClaudeRunnerError("ANTHROPIC_API_KEY not set", transient=False)])
    )
    assert s.failed == 1 and s.retried == 0
    row = _status(repo, req.id)
    assert row.status == "failed" and row.error_message == "ANTHROPIC_API_KEY not set"


def test_garbage_response_fails_with_parse_message(repo):
    req = _request(repo, fmt="modern", colors="R", archetype="aggro")
    process_pending_suggestions(repo, FakeRunner(["isto não é json"]))
    row = _status(repo, req.id)
    assert row.status == "failed"
    assert row.error_message.startswith("Resposta inválida do Claude")


def test_unexpected_exception_isolated_next_request_processed(repo):
    first = _request(repo, fmt="modern", colors="R", archetype="aggro")
    second = _request(repo, fmt="modern", colors="R", archetype="aggro")
    _set_created(repo, first.id, datetime.now() - timedelta(minutes=5))
    real_enrich = processor.enrich
    calls = {"n": 0}

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return real_enrich(*args, **kwargs)

    with patch.object(processor, "enrich", side_effect=flaky):
        s = process_pending_suggestions(repo, FakeRunner([_reply([("Mountain", 60)])]))
    assert s == ProcessSummary(total=2, done=1, failed=1)
    assert _status(repo, first.id).status == "failed"
    assert _status(repo, first.id).error_message == "boom"
    assert _status(repo, second.id).status == "done"


def test_unexpected_exception_without_message_uses_type_name(repo):
    req = _request(repo, fmt="modern", colors="R", archetype="aggro")
    with patch.object(processor, "enrich", side_effect=KeyError()):
        process_pending_suggestions(repo, FakeRunner([_reply([("Mountain", 60)])]))
    assert _status(repo, req.id).error_message == "KeyError"


# --------------------------------------------------------------------------- boundaries


def test_limit_one_processes_only_oldest(repo):
    reqs = [_request(repo, fmt="modern", colors="R", archetype="aggro") for _ in range(3)]
    base = datetime.now() - timedelta(hours=1)
    for i, r in enumerate(reqs):
        _set_created(repo, r.id, base + timedelta(minutes=i))
    s = process_pending_suggestions(repo, FakeRunner([_reply([("Mountain", 60)])]), limit=1)
    assert s.total == 1
    assert [_status(repo, r.id).status for r in reqs] == ["done", "pending", "pending"]


def test_no_pending_requests(repo):
    assert process_pending_suggestions(repo, FakeRunner(["x"])) == ProcessSummary()


def test_dry_run_changes_nothing(repo):
    reqs = [_request(repo, fmt="modern", colors="R", archetype="aggro") for _ in range(3)]
    runner = FakeRunner([_reply([("Mountain", 60)])])
    s = process_pending_suggestions(repo, runner, limit=2, dry_run=True)
    assert s == ProcessSummary(total=2)
    assert runner.prompts == []
    for r in reqs:
        row = _status(repo, r.id)
        assert row.status == "pending" and row.attempts == 0 and row.result_json is None


# --------------------------------------------------------------------------- units


def test_load_owned_cards_prices_and_unlinked(repo):
    ring = _card(repo, "Sol Ring", name_pt="Anel Solar")
    _own(repo, ring, 2)
    _own(repo, None, 3, name_en="Unknown Card", name_pt="Carta Desconhecida")
    _own(repo, None, 1, name_en=None)  # no name at all → skipped
    _own(repo, ring, 5, user="other")
    _price(repo, ring, "12.345")

    coll = load_owned_cards(repo, USER)
    assert [c.name_en for c in coll.linked] == ["Sol Ring"]
    assert coll.linked[0].unit_price == pytest.approx(12.35, abs=0.01)
    assert coll.linked[0].color_identity == ""
    assert [c.name_en for c in coll.unlinked] == ["Unknown Card"]
    assert coll.unlinked[0].color_identity is None
    assert coll.card_ids == {ring}
    qty = coll.quantities_by_name()
    assert qty["sol ring"] == 2 and qty["anel solar"] == 2 and qty["carta desconhecida"] == 3


def test_load_owned_cards_without_price(repo):
    ring = _card(repo, "Sol Ring")
    _own(repo, ring, 1)
    assert load_owned_cards(repo, USER).linked[0].unit_price is None


def test_for_prompt_includes_unlinked_only_for_three_plus_colors():
    coll = OwnedCollection(
        linked=[OwnedCard("Sol Ring", None, 1, "", None, None)],
        unlinked=[OwnedCard("Mystery", None, 1, None, None, None)],
    )
    assert [c.name_en for c in coll.for_prompt(["W", "U"])] == ["Sol Ring"]
    names = {c.name_en for c in coll.for_prompt(["W", "U", "B"])}
    assert names == {"Sol Ring", "Mystery"}


def test_resolve_prefers_owned_printing(repo):
    a = _card(repo, "Sol Ring", set_code="c21", image=None)
    b = _card(repo, "Sol Ring", set_code="cmr")
    c = _card(repo, "Sol Ring", set_code="ltc", image=None)
    assert resolve_cards(repo.engine, ["Sol Ring"], {a})["sol ring"]["card_id"] == a
    # no owned printing → the one with an image wins over a newer id
    assert resolve_cards(repo.engine, ["sol ring"])["sol ring"]["card_id"] == b
    assert c > b


def test_resolve_owned_printing_used_end_to_end(repo):
    a = _card(repo, "Sol Ring", set_code="c21")
    _card(repo, "Sol Ring", set_code="cmr")
    _own(repo, a, 1)
    req = _request(repo, fmt="modern", colors="C", archetype="ramp")
    process_pending_suggestions(repo, FakeRunner([_reply([("Sol Ring", 1)])]))
    card = _result(repo, req.id)["cards"][0]
    assert card["card_id"] == a and card["set_code"] == "c21" and card["is_owned"]


def test_resolve_edge_cases(repo):
    front = _card(repo, "Fable of the Mirror-Breaker")
    assert resolve_cards(repo.engine, []) == {}
    assert resolve_cards(repo.engine, ["  ", ""]) == {}
    got = resolve_cards(
        repo.engine,
        ["Fable of the Mirror-Breaker // Reflection of Kiki-Jiki", "100%_weird", "Nope"],
    )
    assert got["fable of the mirror-breaker // reflection of kiki-jiki"]["card_id"] == front
    assert "100%_weird" not in got and "nope" not in got


def test_resolve_ignores_non_magic_cards(repo):
    with Session(repo.engine) as s:
        s.add(CardRow(game="pokemon", name_en="Pikachu"))
        s.commit()
    assert resolve_cards(repo.engine, ["Pikachu"]) == {}


def test_resolve_chunks_large_lists(repo, monkeypatch):
    monkeypatch.setattr(processor, "RESOLVE_CHUNK", 2)
    ids = [_card(repo, f"Card {i}") for i in range(5)]
    got = resolve_cards(repo.engine, [f"Card {i}" for i in range(5)] + ["Missing A", "Missing B"])
    assert sorted(v["card_id"] for v in got.values()) == ids


class _Req:
    def __init__(self, fmt="modern", commander_name=None, commander_card_id=None):
        self.format_name = fmt
        self.commander_name = commander_name
        self.commander_card_id = commander_card_id


def test_enrich_is_pure_and_computes_costs():
    parsed = ParsedSuggestion(
        deck_name="D", strategy="S",
        cards=[ParsedCard("Sol Ring", 2, "Ramp", "r"), ParsedCard("Island", 58, "Land", "")],
        warnings=["w0"],
    )
    resolved = {"sol ring": {"card_id": 1, "name_en": "Sol Ring", "set_code": "x",
                             "collector_number": "1", "image_uri": None}}
    out = enrich(parsed, _Req(), {"sol ring": 1}, resolved, {1: 3.333}, provider="p", model="m")
    ring = out["cards"][0]
    assert ring["missing_quantity"] == 1 and ring["missing_cost"] == 3.33
    assert out["summary"] == {"total_cards": 60, "owned_cards": 59, "missing_cards": 1,
                              "missing_cost_brl": 3.33, "unresolved_count": 0}
    assert out["warnings"] == ["w0"]
    assert out["provider"] == "p"


def test_enrich_size_mismatch_warning_and_unresolved_commander_keeps_id():
    parsed = ParsedSuggestion(deck_name="D", strategy="S", cards=[ParsedCard("Forest", 10, "", "")])
    out = enrich(parsed, _Req("commander", "Ghost Commander", 77), {}, {}, {})
    assert out["commander"]["card_id"] == 77
    assert out["commander"]["missing_quantity"] == 1
    assert out["summary"]["total_cards"] == 11
    assert any("esperado: 100" in w for w in out["warnings"])
    assert out["summary"]["missing_cost_brl"] is None


def test_prompt_uses_sample_owned_cards_filtered_by_colors(repo):
    coll = OwnedCollection(linked=_sample_owned_cards())
    assert [c.name_en for c in coll.for_prompt(["R"])] == ["Sol Ring"]

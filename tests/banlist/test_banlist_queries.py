"""Tests for F177-T04 grouped banlist queries and status."""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.banlist_queries import get_banlist_status, list_banlist_grouped
from src.database.models import (
    Base,
    CardLegalityRow,
    CardRow,
    LegalityHistoryRow,
    UserCollectionRow,
)


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


def _add_card(session, name_en, name_pt=None, set_code="set1", collector_number="1"):
    card = CardRow(
        game="magic",
        name_en=name_en,
        name_pt=name_pt,
        set_code=set_code,
        collector_number=collector_number,
    )
    session.add(card)
    session.flush()
    return card.id


def _add_legality(session, card_id, format_, status, effective_date=None, updated_at=None):
    legality = CardLegalityRow(
        card_id=card_id,
        format=format_,
        status=status,
        effective_date=effective_date,
    )
    if updated_at is not None:
        legality.updated_at = updated_at
    session.add(legality)


def _add_collection(session, user_id, card_id=None, name_en=None, quantity=1):
    session.add(
        UserCollectionRow(
            user_id=user_id,
            card_id=card_id,
            set_code="set1",
            collector_number="1",
            name_en=name_en,
            quantity=quantity,
        )
    )


class TestListBanlistGrouped:
    def test_groups_multiple_printings_into_one_entry(self, engine):
        with Session(engine) as session:
            id1 = _add_card(session, "Balance", set_code="lea", collector_number="1")
            id2 = _add_card(session, "Balance", set_code="4ed", collector_number="2")
            id3 = _add_card(session, "Balance", set_code="leb", collector_number="3")
            for cid in (id1, id2, id3):
                _add_legality(session, cid, "vintage", "banned")
            session.commit()

        entries, total = list_banlist_grouped(engine, "vintage")
        assert total == 1
        assert entries[0]["printings"] == 3
        assert entries[0]["name_en"] == "Balance"

    def test_status_none_returns_banned_and_restricted_with_correct_total(self, engine):
        with Session(engine) as session:
            banned_id = _add_card(session, "Black Lotus")
            restricted_id = _add_card(session, "Ancestral Recall", set_code="lea2")
            legal_id = _add_card(session, "Forest", set_code="lea3")
            _add_legality(session, banned_id, "vintage", "banned")
            _add_legality(session, restricted_id, "vintage", "restricted")
            _add_legality(session, legal_id, "vintage", "legal")
            session.commit()

        entries, total = list_banlist_grouped(engine, "vintage", offset=0, limit=50)
        assert total == 2
        statuses = {e["name_en"]: e["status"] for e in entries}
        assert statuses == {"Black Lotus": "banned", "Ancestral Recall": "restricted"}

    def test_ordering_banned_before_restricted_then_alphabetical(self, engine):
        with Session(engine) as session:
            zeta = _add_card(session, "Zeta Banned")
            alpha = _add_card(session, "Alpha Banned", set_code="lea2")
            rest = _add_card(session, "Mid Restricted", set_code="lea3")
            _add_legality(session, zeta, "vintage", "banned")
            _add_legality(session, alpha, "vintage", "banned")
            _add_legality(session, rest, "vintage", "restricted")
            session.commit()

        entries, _ = list_banlist_grouped(engine, "vintage")
        names = [e["name_en"] for e in entries]
        assert names == ["Alpha Banned", "Zeta Banned", "Mid Restricted"]

    def test_status_filter_returns_only_that_status(self, engine):
        with Session(engine) as session:
            banned_id = _add_card(session, "Black Lotus")
            restricted_id = _add_card(session, "Ancestral Recall", set_code="lea2")
            _add_legality(session, banned_id, "vintage", "banned")
            _add_legality(session, restricted_id, "vintage", "restricted")
            session.commit()

        entries, total = list_banlist_grouped(engine, "vintage", status="banned")
        assert total == 1
        assert entries[0]["name_en"] == "Black Lotus"

    def test_owned_by_card_id_match(self, engine):
        with Session(engine) as session:
            cid = _add_card(session, "Channel")
            _add_legality(session, cid, "vintage", "banned")
            _add_collection(session, "user1", card_id=cid, quantity=2)
            session.commit()

        entries, _ = list_banlist_grouped(engine, "vintage", user_id="user1")
        assert entries[0]["owned"] is True
        assert entries[0]["owned_quantity"] == 2

    def test_owned_by_name_only_match_unlinked_row(self, engine):
        with Session(engine) as session:
            cid = _add_card(session, "Channel")
            _add_legality(session, cid, "vintage", "banned")
            _add_collection(session, "user1", card_id=None, name_en="Channel", quantity=3)
            session.commit()

        entries, _ = list_banlist_grouped(engine, "vintage", user_id="user1")
        assert entries[0]["owned"] is True
        assert entries[0]["owned_quantity"] == 3

    def test_owned_representative_chosen_over_lowest_card_id(self, engine):
        with Session(engine) as session:
            lowest_id = _add_card(session, "Balance", set_code="lea")
            owned_id = _add_card(session, "Balance", set_code="4ed")
            _add_legality(session, lowest_id, "vintage", "banned")
            _add_legality(session, owned_id, "vintage", "banned")
            _add_collection(session, "user1", card_id=owned_id, quantity=1)
            session.commit()

        entries, _ = list_banlist_grouped(engine, "vintage", user_id="user1")
        assert entries[0]["card_id"] == owned_id
        assert entries[0]["set_code"] == "4ed"

    def test_different_user_collection_not_owned(self, engine):
        with Session(engine) as session:
            cid = _add_card(session, "Channel")
            _add_legality(session, cid, "vintage", "banned")
            _add_collection(session, "other_user", card_id=cid, quantity=5)
            session.commit()

        entries, _ = list_banlist_grouped(engine, "vintage", user_id="user1")
        assert entries[0]["owned"] is False
        assert entries[0]["owned_quantity"] == 0

    def test_owned_only_without_user_id_returns_empty(self, engine):
        with Session(engine) as session:
            cid = _add_card(session, "Channel")
            _add_legality(session, cid, "vintage", "banned")
            session.commit()

        entries, total = list_banlist_grouped(engine, "vintage", owned_only=True, user_id=None)
        assert entries == []
        assert total == 0

    def test_owned_only_filters_out_unowned(self, engine):
        with Session(engine) as session:
            owned_id = _add_card(session, "Channel")
            unowned_id = _add_card(session, "Balance", set_code="lea2")
            _add_legality(session, owned_id, "vintage", "banned")
            _add_legality(session, unowned_id, "vintage", "banned")
            _add_collection(session, "user1", card_id=owned_id, quantity=1)
            session.commit()

        entries, total = list_banlist_grouped(
            engine, "vintage", owned_only=True, user_id="user1"
        )
        assert total == 1
        assert entries[0]["name_en"] == "Channel"

    def test_search_matches_name_en_case_insensitive(self, engine):
        with Session(engine) as session:
            cid = _add_card(session, "Black Lotus")
            _add_legality(session, cid, "vintage", "banned")
            session.commit()

        entries, total = list_banlist_grouped(engine, "vintage", search="black lotus")
        assert total == 1

        entries, total = list_banlist_grouped(engine, "vintage", search="lotus")
        assert total == 1

    def test_search_matches_name_pt_case_insensitive(self, engine):
        with Session(engine) as session:
            cid = _add_card(session, "Black Lotus", name_pt="Lotus Negro")
            _add_legality(session, cid, "vintage", "banned")
            session.commit()

        entries, total = list_banlist_grouped(engine, "vintage", search="NEGRO")
        assert total == 1

    def test_search_no_matches_returns_empty(self, engine):
        with Session(engine) as session:
            cid = _add_card(session, "Black Lotus")
            _add_legality(session, cid, "vintage", "banned")
            session.commit()

        entries, total = list_banlist_grouped(engine, "vintage", search="nonexistent")
        assert entries == []
        assert total == 0

    def test_pagination_limit_and_offset(self, engine):
        with Session(engine) as session:
            for name in ["Alpha", "Beta", "Gamma"]:
                cid = _add_card(session, name, set_code=name.lower())
                _add_legality(session, cid, "vintage", "banned")
            session.commit()

        entries, total = list_banlist_grouped(engine, "vintage", limit=1, offset=1)
        assert total == 3
        assert len(entries) == 1
        assert entries[0]["name_en"] == "Beta"

    def test_pagination_offset_beyond_total_returns_empty(self, engine):
        with Session(engine) as session:
            cid = _add_card(session, "Alpha")
            _add_legality(session, cid, "vintage", "banned")
            session.commit()

        entries, total = list_banlist_grouped(engine, "vintage", limit=50, offset=10)
        assert entries == []
        assert total == 1

    def test_invalid_status_raises_value_error(self, engine):
        with pytest.raises(ValueError):
            list_banlist_grouped(engine, "vintage", status="legal")

    def test_name_en_blank_grouped_under_empty_string_without_crashing(self, engine):
        with Session(engine) as session:
            card = CardRow(game="magic", name_en="", set_code="x", collector_number="1")
            session.add(card)
            session.flush()
            _add_legality(session, card.id, "vintage", "banned")
            session.commit()

        entries, total = list_banlist_grouped(engine, "vintage")
        assert total == 1
        assert entries[0]["name_en"] == ""

    def test_group_status_takes_most_severe(self, engine):
        with Session(engine) as session:
            id1 = _add_card(session, "Splitcard", set_code="lea")
            id2 = _add_card(session, "Splitcard", set_code="leb")
            _add_legality(session, id1, "vintage", "restricted")
            _add_legality(session, id2, "vintage", "banned")
            session.commit()

        entries, _ = list_banlist_grouped(engine, "vintage")
        assert entries[0]["status"] == "banned"

    def test_effective_date_is_max_across_printings(self, engine):
        with Session(engine) as session:
            id1 = _add_card(session, "Splitcard", set_code="lea")
            id2 = _add_card(session, "Splitcard", set_code="leb")
            _add_legality(session, id1, "vintage", "banned", effective_date=date(2020, 1, 1))
            _add_legality(session, id2, "vintage", "banned", effective_date=date(2021, 1, 1))
            session.commit()

        entries, _ = list_banlist_grouped(engine, "vintage")
        assert entries[0]["effective_date"] == date(2021, 1, 1)

    def test_effective_date_none_when_all_none(self, engine):
        with Session(engine) as session:
            cid = _add_card(session, "Splitcard")
            _add_legality(session, cid, "vintage", "banned")
            session.commit()

        entries, _ = list_banlist_grouped(engine, "vintage")
        assert entries[0]["effective_date"] is None


class TestGetBanlistStatus:
    def test_empty_db_returns_zeros_and_none(self, engine):
        status = get_banlist_status(engine)
        assert status == {
            "last_synced_at": None,
            "legalities_count": 0,
            "banned_count": 0,
            "restricted_count": 0,
            "history_count": 0,
            "formats": 0,
        }

    def test_counts_and_formats(self, engine):
        with Session(engine) as session:
            id1 = _add_card(session, "A")
            id2 = _add_card(session, "B", set_code="x2")
            id3 = _add_card(session, "C", set_code="x3")
            _add_legality(session, id1, "vintage", "banned")
            _add_legality(session, id2, "vintage", "restricted")
            _add_legality(session, id3, "legacy", "banned")
            session.add(
                LegalityHistoryRow(
                    card_id=id1,
                    format="vintage",
                    old_status=None,
                    new_status="banned",
                    changed_at=datetime(2024, 1, 1),
                )
            )
            session.commit()

        status = get_banlist_status(engine)
        assert status["legalities_count"] == 3
        assert status["banned_count"] == 2
        assert status["restricted_count"] == 1
        assert status["history_count"] == 1
        assert status["formats"] == 2
        assert status["last_synced_at"] is not None

    def test_last_synced_at_is_max_updated_at(self, engine):
        with Session(engine) as session:
            id1 = _add_card(session, "A")
            id2 = _add_card(session, "B", set_code="x2")
            _add_legality(session, id1, "vintage", "banned", updated_at=datetime(2023, 1, 1))
            _add_legality(session, id2, "vintage", "banned", updated_at=datetime(2024, 6, 1))
            session.commit()

        status = get_banlist_status(engine)
        assert status["last_synced_at"] == datetime(2024, 6, 1)

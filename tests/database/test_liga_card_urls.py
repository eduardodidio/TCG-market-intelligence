"""Tests for LigaCardUrlRow model + repository upsert/get (F124-T02)."""

from __future__ import annotations

import pytest

from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "t.db"
    return Repository(f"sqlite:///{db_path}")


class TestLigaCardUrlUpsertAndGet:
    def test_insert_then_get(self, repo):
        repo.upsert_liga_card_url("liga_42", "https://www.ligamagic.com.br/?view=cards/card&card=Foo&show=1")

        assert repo.get_liga_card_url("liga_42") == (
            "https://www.ligamagic.com.br/?view=cards/card&card=Foo&show=1"
        )

    def test_upsert_updates_existing_key(self, repo):
        repo.upsert_liga_card_url("liga_42", "https://www.ligamagic.com.br/?view=cards/card&card=Foo&show=1")
        repo.upsert_liga_card_url("liga_42", "https://www.ligamagic.com.br/?view=cards/card&card=Bar&show=1")

        assert repo.get_liga_card_url("liga_42") == (
            "https://www.ligamagic.com.br/?view=cards/card&card=Bar&show=1"
        )

    def test_update_advances_updated_at(self, repo):
        from sqlalchemy.orm import Session

        from src.database.models import LigaCardUrlRow

        repo.upsert_liga_card_url("liga_42", "https://www.ligamagic.com.br/?view=cards/card&card=Foo&show=1")
        with Session(repo.engine) as session:
            first_updated_at = session.get(LigaCardUrlRow, "liga_42").updated_at

        repo.upsert_liga_card_url("liga_42", "https://www.ligamagic.com.br/?view=cards/card&card=Bar&show=1")
        with Session(repo.engine) as session:
            second_updated_at = session.get(LigaCardUrlRow, "liga_42").updated_at

        assert second_updated_at >= first_updated_at

    def test_independent_keys_normal_and_foil(self, repo):
        repo.upsert_liga_card_url("liga_42", "https://www.ligamagic.com.br/?view=cards/card&card=Foo&show=1")
        repo.upsert_liga_card_url(
            "liga_42_foil", "https://www.ligamagic.com.br/?view=cards/card&card=Foo+Foil&show=1"
        )

        assert repo.get_liga_card_url("liga_42") == (
            "https://www.ligamagic.com.br/?view=cards/card&card=Foo&show=1"
        )
        assert repo.get_liga_card_url("liga_42_foil") == (
            "https://www.ligamagic.com.br/?view=cards/card&card=Foo+Foil&show=1"
        )

    def test_unknown_key_returns_none(self, repo):
        assert repo.get_liga_card_url("liga_does_not_exist") is None

    def test_idempotent_upsert_same_value(self, repo):
        from sqlalchemy import func, select
        from sqlalchemy.orm import Session

        from src.database.models import LigaCardUrlRow

        url = "https://www.ligamagic.com.br/?view=cards/card&card=Foo&show=1"
        repo.upsert_liga_card_url("liga_42", url)
        repo.upsert_liga_card_url("liga_42", url)

        with Session(repo.engine) as session:
            count = session.scalar(select(func.count()).select_from(LigaCardUrlRow))

        assert count == 1


class TestLigaCardUrlValidation:
    def test_empty_external_id_raises(self, repo):
        with pytest.raises(ValueError):
            repo.upsert_liga_card_url("", "https://www.ligamagic.com.br/?view=cards/card&card=Foo&show=1")

    def test_empty_url_raises(self, repo):
        with pytest.raises(ValueError):
            repo.upsert_liga_card_url("liga_42", "")

    def test_url_over_1000_chars_raises(self, repo):
        long_url = "https://www.ligamagic.com.br/?view=cards/card&card=" + "a" * 950
        assert len(long_url) == 1001
        with pytest.raises(ValueError):
            repo.upsert_liga_card_url("liga_42", long_url)

    def test_url_exactly_1000_chars_accepted(self, repo):
        long_url = "https://www.ligamagic.com.br/?view=cards/card&card=" + "a" * 949
        assert len(long_url) == 1000
        repo.upsert_liga_card_url("liga_42", long_url)

        assert repo.get_liga_card_url("liga_42") == long_url

"""Tests for UTF-8 double-encoding fix in provider and migration script."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts.fix_encoding import fix_mojibake
from src.providers.myp.provider import MypCardsProvider, MypConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config():
    return MypConfig(delay_seconds=0, max_retries=2, timeout_seconds=1)


@pytest.fixture
def provider(config):
    return MypCardsProvider(config)


# ---------------------------------------------------------------------------
# Provider _fetch UTF-8 handling
# ---------------------------------------------------------------------------


class TestFetchUtf8:
    """Verify that _fetch always returns correctly decoded UTF-8."""

    @pytest.mark.asyncio
    async def test_fetch_forces_utf8_decoding(self, provider):
        """When response body is UTF-8 bytes, _fetch decodes them correctly
        regardless of what the Content-Type header says."""
        # Simulate curl_cffi response with UTF-8 content bytes
        utf8_html = "<html><title>Contramágica</title></html>"
        utf8_bytes = utf8_html.encode("utf-8")

        resp = MagicMock()
        resp.status_code = 200
        # .text would be wrong if curl_cffi used latin-1 to decode
        resp.text = utf8_bytes.decode("latin-1")  # mojibake
        # .content is raw bytes
        resp.content = utf8_bytes

        mock_session = AsyncMock()
        mock_session.get.return_value = resp
        provider._session = mock_session

        result = await provider._fetch("https://example.com")

        # Must match the original UTF-8 string, not the latin-1 mojibake
        assert result == utf8_html
        assert "Contramágica" in result

    @pytest.mark.asyncio
    async def test_fetch_handles_ascii_content(self, provider):
        """ASCII-only content works the same with forced UTF-8 decode."""
        ascii_html = "<html><title>Lightning Bolt</title></html>"

        resp = MagicMock()
        resp.status_code = 200
        resp.content = ascii_html.encode("utf-8")

        mock_session = AsyncMock()
        mock_session.get.return_value = resp
        provider._session = mock_session

        result = await provider._fetch("https://example.com")
        assert result == ascii_html

    @pytest.mark.asyncio
    async def test_fetch_handles_empty_response_body(self, provider):
        """Empty response body decodes to empty string."""
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b""

        mock_session = AsyncMock()
        mock_session.get.return_value = resp
        provider._session = mock_session

        result = await provider._fetch("https://example.com")
        assert result == ""

    @pytest.mark.asyncio
    async def test_fetch_preserves_portuguese_accents(self, provider):
        """Full Portuguese card name with multiple accented chars."""
        pt_html = "<html><title>Relâmpago Hélice — Edição Especial</title></html>"
        utf8_bytes = pt_html.encode("utf-8")

        resp = MagicMock()
        resp.status_code = 200
        resp.content = utf8_bytes

        mock_session = AsyncMock()
        mock_session.get.return_value = resp
        provider._session = mock_session

        result = await provider._fetch("https://example.com")
        assert "Relâmpago" in result
        assert "Hélice" in result
        assert "Edição" in result


# ---------------------------------------------------------------------------
# fix_mojibake function
# ---------------------------------------------------------------------------


class TestFixMojibake:
    """Test the mojibake detection and fix logic."""

    def test_fixes_double_encoded_a_acute(self):
        """'á' double-encoded through latin-1 produces 'Ã¡'."""
        # "Contramágica" encoded as UTF-8, then decoded as latin-1
        mojibake = "Contramágica".encode("utf-8").decode("latin-1")
        fixed, changed = fix_mojibake(mojibake)
        assert fixed == "Contramágica"
        assert changed is True

    def test_fixes_double_encoded_a_circumflex(self):
        """'â' double-encoded through latin-1."""
        mojibake = "Relâmpago Hélice".encode("utf-8").decode("latin-1")
        fixed, changed = fix_mojibake(mojibake)
        assert fixed == "Relâmpago Hélice"
        assert changed is True

    def test_fixes_double_encoded_cedilla(self):
        """'ç' double-encoded through latin-1."""
        mojibake = "Edição".encode("utf-8").decode("latin-1")
        fixed, changed = fix_mojibake(mojibake)
        assert fixed == "Edição"
        assert changed is True

    def test_already_correct_text_unchanged(self):
        """Text that is already correct UTF-8 is not modified."""
        correct = "Contramágica"
        fixed, changed = fix_mojibake(correct)
        assert fixed == correct
        assert changed is False

    def test_ascii_text_unchanged(self):
        """Pure ASCII text passes through unchanged."""
        ascii_text = "Lightning Bolt"
        fixed, changed = fix_mojibake(ascii_text)
        assert fixed == ascii_text
        assert changed is False

    def test_none_returns_none(self):
        """None input returns (None, False)."""
        fixed, changed = fix_mojibake(None)
        assert fixed is None
        assert changed is False

    def test_empty_string_unchanged(self):
        """Empty string passes through unchanged."""
        fixed, changed = fix_mojibake("")
        assert fixed == ""
        assert changed is False

    def test_handles_unencodable_latin1_gracefully(self):
        """Text with characters outside latin-1 range (e.g., CJK, emoji)
        cannot be encoded as latin-1, so fix_mojibake returns it unchanged."""
        # CJK characters cannot be encoded to latin-1
        cjk_text = "\u4e16\u754c"  # "world" in Chinese
        fixed, changed = fix_mojibake(cjk_text)
        assert fixed == cjk_text
        assert changed is False

    def test_idempotent_on_already_fixed(self):
        """Running fix_mojibake twice on corrected text is safe."""
        mojibake = "Contramágica".encode("utf-8").decode("latin-1")
        fixed_once, _ = fix_mojibake(mojibake)
        fixed_twice, changed = fix_mojibake(fixed_once)
        assert fixed_twice == "Contramágica"
        assert changed is False


# ---------------------------------------------------------------------------
# Migration script integration (in-memory DB)
# ---------------------------------------------------------------------------


class TestMigrationScript:
    """Test the full migration flow with an in-memory SQLite database."""

    def test_migration_fixes_mojibake_rows(self):
        """Migration fixes double-encoded names in both tables."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from scripts.fix_encoding import fix_cards, fix_source_cards
        from src.database.models import Base, CardRow, SourceCardRow

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        # Create mojibake data
        mojibake_name = "Contramágica".encode("utf-8").decode("latin-1")

        with Session(engine) as session:
            session.add(
                SourceCardRow(
                    source="myp",
                    external_id="123",
                    url="https://mypcards.com/magic/produto/123/contramagica",
                    name_en=mojibake_name,
                    name_pt=mojibake_name,
                )
            )
            session.add(
                CardRow(
                    game="magic",
                    name_en=mojibake_name,
                    name_pt=mojibake_name,
                    set_code="DMR",
                    collector_number="1",
                )
            )
            session.commit()

        # Run the fix
        with Session(engine) as session:
            sc_fixed = fix_source_cards(session)
            c_fixed = fix_cards(session)
            session.commit()

        assert sc_fixed == 1
        assert c_fixed == 1

        # Verify the data is correct
        with Session(engine) as session:
            sc = session.execute(
                session.query(SourceCardRow).filter_by(external_id="123").statement
            ).scalar_one()
            assert sc.name_en == "Contramágica"
            assert sc.name_pt == "Contramágica"

            card = session.execute(
                session.query(CardRow).filter_by(set_code="DMR").statement
            ).scalar_one()
            assert card.name_en == "Contramágica"
            assert card.name_pt == "Contramágica"

    def test_migration_idempotent(self):
        """Running migration twice does not modify already-correct rows."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from scripts.fix_encoding import fix_cards, fix_source_cards
        from src.database.models import Base, CardRow, SourceCardRow

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        # Insert already-correct data
        with Session(engine) as session:
            session.add(
                SourceCardRow(
                    source="myp",
                    external_id="456",
                    url="https://mypcards.com/magic/produto/456/test",
                    name_en="Contramágica",
                    name_pt="Contramágica",
                )
            )
            session.add(
                CardRow(
                    game="magic",
                    name_en="Contramágica",
                    name_pt="Contramágica",
                    set_code="DMR",
                    collector_number="2",
                )
            )
            session.commit()

        # Run the fix -- should find nothing to fix
        with Session(engine) as session:
            sc_fixed = fix_source_cards(session)
            c_fixed = fix_cards(session)
            session.commit()

        assert sc_fixed == 0
        assert c_fixed == 0

    def test_migration_dry_run_does_not_modify(self):
        """Dry run reports fixes but does not change the database."""
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        from scripts.fix_encoding import fix_source_cards
        from src.database.models import Base, SourceCardRow

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        mojibake_name = "Contramágica".encode("utf-8").decode("latin-1")

        with Session(engine) as session:
            session.add(
                SourceCardRow(
                    source="myp",
                    external_id="789",
                    url="https://mypcards.com/magic/produto/789/test",
                    name_en=mojibake_name,
                    name_pt=mojibake_name,
                )
            )
            session.commit()

        # Dry run
        with Session(engine) as session:
            sc_fixed = fix_source_cards(session, dry_run=True)
            # Do NOT commit

        assert sc_fixed == 1

        # Verify data was NOT modified
        with Session(engine) as session:
            row = session.execute(
                select(SourceCardRow).where(SourceCardRow.external_id == "789")
            ).scalar_one()
            assert row.name_en == mojibake_name  # still mojibake

    def test_main_function_runs(self):
        """The main() function runs end-to-end on an in-memory DB."""
        from scripts.fix_encoding import main

        summary = main(db_url="sqlite:///:memory:", dry_run=False)
        assert summary["source_cards_fixed"] == 0
        assert summary["cards_fixed"] == 0

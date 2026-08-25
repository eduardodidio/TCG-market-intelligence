"""Tests for the Liga scan wrapper (F60-T04).

Covers:
 1. run_liga_scan calls run_scan with provider_name="liga"
 2. Default delay is 5.0
 3. Provider cleanup in finally block (success and error)
 4. db_url defaults to get_db_url()
 5. dry_run parameter passed through
 6. max_age_days parameter passed through
 7. scan_filter parameter passed through
 8. run_id and on_complete passed through
 9. LigaMagicProvider is never instantiated for real (mocked)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.models import ScanFilter, ScanRun, ScanType

# ── helpers ──────────────────────────────────────────────────────


def _fake_scan_run(**overrides) -> ScanRun:
    """Build a minimal ScanRun for test returns."""
    defaults = {
        "id": 1,
        "scan_type": "liga_full",
        "filters_json": "{}",
        "status": "completed",
        "cards_total": 0,
        "cards_processed": 0,
        "cards_failed": 0,
        "observations_saved": 0,
        "error_summary": None,
        "started_at": None,
        "finished_at": None,
    }
    defaults.update(overrides)
    return ScanRun(**defaults)


# ── tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRunLigaScan:
    """Tests for the run_liga_scan thin wrapper."""

    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_calls_run_scan_with_liga_provider_name(self, mock_run_scan, MockProvider):
        """run_liga_scan passes provider_name='liga' to run_scan."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        mock_run_scan.return_value = _fake_scan_run()

        await run_liga_scan(db_url="sqlite:///:memory:")

        mock_run_scan.assert_awaited_once()
        call_kwargs = mock_run_scan.call_args[1]
        assert call_kwargs["provider_name"] == "liga"

    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_passes_provider_instance(self, mock_run_scan, MockProvider):
        """run_liga_scan passes the LigaMagicProvider instance to run_scan."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        mock_run_scan.return_value = _fake_scan_run()

        await run_liga_scan(db_url="sqlite:///:memory:")

        call_kwargs = mock_run_scan.call_args[1]
        assert call_kwargs["provider"] is provider

    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_default_delay_is_5(self, mock_run_scan, MockProvider):
        """Default delay parameter is 5.0 seconds."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        mock_run_scan.return_value = _fake_scan_run()

        await run_liga_scan(db_url="sqlite:///:memory:")

        call_kwargs = mock_run_scan.call_args[1]
        assert call_kwargs["delay"] == 5.0

    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_custom_delay_passed_through(self, mock_run_scan, MockProvider):
        """Custom delay value is forwarded to run_scan."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        mock_run_scan.return_value = _fake_scan_run()

        await run_liga_scan(db_url="sqlite:///:memory:", delay=10.0)

        call_kwargs = mock_run_scan.call_args[1]
        assert call_kwargs["delay"] == 10.0

    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_provider_closed_on_success(self, mock_run_scan, MockProvider):
        """Provider.close() is called after a successful scan."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        mock_run_scan.return_value = _fake_scan_run()

        await run_liga_scan(db_url="sqlite:///:memory:")

        provider.close.assert_awaited_once()

    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_provider_closed_on_error(self, mock_run_scan, MockProvider):
        """Provider.close() is called even when run_scan raises."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        mock_run_scan.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await run_liga_scan(db_url="sqlite:///:memory:")

        provider.close.assert_awaited_once()

    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_provider_opened_before_scan(self, mock_run_scan, MockProvider):
        """Provider.open() is called before run_scan."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        mock_run_scan.return_value = _fake_scan_run()

        await run_liga_scan(db_url="sqlite:///:memory:")

        provider.open.assert_awaited_once()

    @patch("src.collectors.liga_scan.get_db_url", return_value="sqlite:///default.db")
    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_db_url_defaults_to_get_db_url(
        self, mock_run_scan, MockProvider, mock_get_db_url
    ):
        """When db_url is None, get_db_url() is used."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        mock_run_scan.return_value = _fake_scan_run()

        await run_liga_scan()

        call_kwargs = mock_run_scan.call_args[1]
        assert call_kwargs["db_url"] == "sqlite:///default.db"
        mock_get_db_url.assert_called_once()

    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_explicit_db_url_used(self, mock_run_scan, MockProvider):
        """When db_url is provided explicitly, it is used directly."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        mock_run_scan.return_value = _fake_scan_run()

        await run_liga_scan(db_url="sqlite:///custom.db")

        call_kwargs = mock_run_scan.call_args[1]
        assert call_kwargs["db_url"] == "sqlite:///custom.db"

    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_dry_run_passed_through(self, mock_run_scan, MockProvider):
        """dry_run parameter is forwarded to run_scan."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        mock_run_scan.return_value = _fake_scan_run()

        await run_liga_scan(db_url="sqlite:///:memory:", dry_run=True)

        call_kwargs = mock_run_scan.call_args[1]
        assert call_kwargs["dry_run"] is True

    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_scan_filter_passed_through(self, mock_run_scan, MockProvider):
        """scan_filter parameter is forwarded to run_scan."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        mock_run_scan.return_value = _fake_scan_run()

        filt = ScanFilter(scan_type=ScanType.CUSTOM, card_ids=[1, 2, 3])
        await run_liga_scan(db_url="sqlite:///:memory:", scan_filter=filt)

        call_kwargs = mock_run_scan.call_args[1]
        assert call_kwargs["scan_filter"] is filt

    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_run_id_passed_through(self, mock_run_scan, MockProvider):
        """run_id parameter is forwarded to run_scan."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        mock_run_scan.return_value = _fake_scan_run()

        await run_liga_scan(db_url="sqlite:///:memory:", run_id=42)

        call_kwargs = mock_run_scan.call_args[1]
        assert call_kwargs["run_id"] == 42

    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_on_complete_passed_through(self, mock_run_scan, MockProvider):
        """on_complete callback is forwarded to run_scan."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        mock_run_scan.return_value = _fake_scan_run()

        callback = MagicMock()
        await run_liga_scan(db_url="sqlite:///:memory:", on_complete=callback)

        call_kwargs = mock_run_scan.call_args[1]
        assert call_kwargs["on_complete"] is callback

    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_max_age_days_accepted(self, mock_run_scan, MockProvider):
        """max_age_days parameter is accepted without error."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        mock_run_scan.return_value = _fake_scan_run()

        # Should not raise
        await run_liga_scan(db_url="sqlite:///:memory:", max_age_days=7)

        mock_run_scan.assert_awaited_once()

    @patch("src.collectors.liga_scan.LigaMagicProvider")
    @patch("src.collectors.liga_scan.run_scan", new_callable=AsyncMock)
    async def test_returns_scan_run(self, mock_run_scan, MockProvider):
        """run_liga_scan returns the ScanRun from run_scan."""
        from src.collectors.liga_scan import run_liga_scan

        provider = MockProvider.return_value
        provider.open = AsyncMock()
        provider.close = AsyncMock()
        expected = _fake_scan_run(cards_processed=5, observations_saved=3)
        mock_run_scan.return_value = expected

        result = await run_liga_scan(db_url="sqlite:///:memory:")

        assert result is expected
        assert result.cards_processed == 5
        assert result.observations_saved == 3

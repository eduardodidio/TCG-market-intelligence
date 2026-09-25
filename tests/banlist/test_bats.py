"""Static regression guard for bats/banlist-sync.bat."""

from pathlib import Path

BAT_PATH = Path(__file__).resolve().parents[2] / "bats" / "banlist-sync.bat"


def test_banlist_sync_bat_exists():
    assert BAT_PATH.exists()


def test_banlist_sync_bat_calls_cli_command():
    content = BAT_PATH.read_text()
    assert "python -m src.cli.main banlist-sync" in content


def test_banlist_sync_bat_handles_errorlevel():
    content = BAT_PATH.read_text()
    assert "errorlevel" in content
    assert "exit /b 1" in content

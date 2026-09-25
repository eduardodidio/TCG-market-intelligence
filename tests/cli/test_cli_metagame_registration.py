"""F173-T15 — ``collect-metagame`` is registered on the main CLI group."""

from __future__ import annotations

import re

from click.testing import CliRunner

from src.cli.main import cli


def test_collect_metagame_help():
    result = CliRunner().invoke(cli, ["collect-metagame", "--help"])
    assert result.exit_code == 0, result.output
    assert "--dry-run" in result.output


def test_collect_metagame_listed_in_cli_help():
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "collect-metagame" in result.output


def test_metagame_module_does_not_import_cli_main():
    """main.py imports metagame.py, so the reverse would be an import cycle."""
    import src.cli.metagame as mod

    source = open(mod.__file__, encoding="utf-8").read()
    assert not re.search(r"^\s*(from src\.cli\.main |import src\.cli\.main)", source, re.M)

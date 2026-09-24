"""Tests for the standalone collect-metagame CLI command (F173-T12)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine, func, select

import src.metagame.sources as sources_mod
from src.cli import metagame as cli_mod
from src.cli.metagame import collect_metagame_cmd
from src.metagame.http import PoliteFetcher
from src.metagame.models import MetaDeckRow
from src.metagame.sources import SOURCE_FOR_FORMAT, get_sources
from src.metagame.sources.base import FORMATS, MetaCardEntry, MetaDeckEntry
from src.metagame.sources.edhrec import EdhrecSource
from src.metagame.sources.mtgtop8 import Mtgtop8Source


def _deck(fmt: str, rank: int) -> MetaDeckEntry:
    return MetaDeckEntry(
        source="fake",
        format=fmt,
        external_id=f"{fmt}-{rank}",
        archetype=f"Arch {rank}",
        rank=rank,
        meta_share_pct=Decimal("10.5"),
        deck_count=None,
        colors="UR",
        commander_name=None,
        source_url=f"https://example.test/{fmt}/{rank}",
        event_date=date(2026, 9, 20),
        cards=(MetaCardEntry(name="Lightning Bolt", quantity=4),),
    )


class FakeSource:
    name = "fake"

    def __init__(self, fail: set[str] | None = None):
        self.fail = fail or set()
        self.calls: list[tuple[str, int]] = []

    def fetch_top_decks(self, fmt, *, limit=20):
        self.calls.append((fmt, limit))
        if fmt in self.fail:
            raise RuntimeError(f"boom {fmt}")
        return [_deck(fmt, r) for r in range(1, limit + 1)]


class FakeFetcher:
    def get_text(self, url, **kw):  # pragma: no cover - never called
        raise AssertionError("network")

    def get_json(self, url, **kw):  # pragma: no cover - never called
        raise AssertionError("network")


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{tmp_path}/t.db"


def _install(monkeypatch, source: FakeSource) -> None:
    monkeypatch.setattr(sources_mod, "get_sources", lambda fetcher: {f: source for f in FORMATS})


def _count(db_url: str) -> int:
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            return conn.execute(select(func.count()).select_from(MetaDeckRow)).scalar_one()
    finally:
        engine.dispose()


def _run(args):
    return CliRunner().invoke(collect_metagame_cmd, args)


# ── registry ────────────────────────────────────────────────────────────────


def test_registry_covers_all_formats():
    assert set(SOURCE_FOR_FORMAT) == set(FORMATS)
    assert SOURCE_FOR_FORMAT["commander"] == "edhrec"
    assert {SOURCE_FOR_FORMAT[f] for f in FORMATS if f != "commander"} == {"mtgtop8"}


def test_get_sources_returns_instance_per_format_shared_by_source():
    result = get_sources(FakeFetcher())
    assert set(result) == set(SOURCE_FOR_FORMAT)
    assert isinstance(result["commander"], EdhrecSource)
    constructed = [result[f] for f in FORMATS if f != "commander"]
    assert all(isinstance(s, Mtgtop8Source) for s in constructed)
    assert len({id(s) for s in constructed}) == 1
    for fmt, src in result.items():
        assert src.name == SOURCE_FOR_FORMAT[fmt]
        assert fmt in src.formats


# ── CLI ─────────────────────────────────────────────────────────────────────


def test_happy_path_writes_and_prints_totals(monkeypatch, db_url):
    src = FakeSource()
    _install(monkeypatch, src)
    result = _run(["-f", "modern", "-f", "commander", "--limit", "2", "--db", db_url])
    assert result.exit_code == 0, result.output
    assert src.calls == [("modern", 2), ("commander", 2)]
    assert "Formats collected: 2/2" in result.output
    assert "Decks:             4" in result.output
    assert "modern" in result.output and "commander" in result.output
    assert _count(db_url) == 4


def test_no_format_collects_all_registry_formats(monkeypatch, db_url):
    src = FakeSource()
    _install(monkeypatch, src)
    result = _run(["--limit", "1", "--db", db_url])
    assert result.exit_code == 0, result.output
    assert [c[0] for c in src.calls] == list(SOURCE_FOR_FORMAT)
    assert f"Formats collected: {len(SOURCE_FOR_FORMAT)}/{len(SOURCE_FOR_FORMAT)}" in result.output


def test_default_limit_is_20(monkeypatch, db_url):
    src = FakeSource()
    _install(monkeypatch, src)
    result = _run(["-f", "pauper", "--db", db_url])
    assert result.exit_code == 0, result.output
    assert src.calls == [("pauper", 20)]


def test_dry_run_writes_nothing(monkeypatch, db_url):
    _install(monkeypatch, FakeSource())
    result = _run(["-f", "modern", "--limit", "3", "--dry-run", "--db", db_url])
    assert result.exit_code == 0, result.output
    assert "(dry run)" in result.output
    assert _count(db_url) == 0


def test_all_sources_fail_exit_1(monkeypatch, db_url):
    _install(monkeypatch, FakeSource(fail={"modern", "legacy"}))
    result = _run(["-f", "modern", "-f", "legacy", "--db", db_url])
    assert result.exit_code == 1
    assert "boom modern" in result.output
    assert "boom legacy" in result.output
    assert "All formats failed" in result.output


def test_partial_failure_exit_0_with_warning(monkeypatch, db_url):
    _install(monkeypatch, FakeSource(fail={"legacy"}))
    result = _run(["-f", "modern", "-f", "legacy", "--limit", "2", "--db", db_url])
    assert result.exit_code == 0, result.output
    assert "WARNING: 1 format(s) failed." in result.output
    assert "legacy: boom legacy" in result.output
    lines = {line.split()[0]: line for line in result.output.splitlines() if line.startswith("  ")}
    assert lines["legacy"].endswith("FAIL")
    assert lines["modern"].endswith("ok")
    assert _count(db_url) == 2


def test_missing_source_counts_as_failure(monkeypatch, db_url):
    monkeypatch.setattr(sources_mod, "get_sources", lambda fetcher: {})
    result = _run(["-f", "vintage", "--db", db_url])
    assert result.exit_code == 1
    assert "no source for vintage" in result.output


@pytest.mark.parametrize("limit", ["0", "51"])
def test_limit_out_of_range_is_usage_error(monkeypatch, db_url, limit):
    _install(monkeypatch, FakeSource())
    result = _run(["--limit", limit, "--db", db_url])
    assert result.exit_code == 2
    assert "Invalid value" in result.output


def test_limit_boundaries_accepted(monkeypatch, db_url):
    src = FakeSource()
    _install(monkeypatch, src)
    assert _run(["-f", "modern", "--limit", "1", "--dry-run", "--db", db_url]).exit_code == 0
    assert _run(["-f", "modern", "--limit", "50", "--dry-run", "--db", db_url]).exit_code == 0
    assert src.calls == [("modern", 1), ("modern", 50)]


def test_invalid_format_is_usage_error(monkeypatch, db_url):
    _install(monkeypatch, FakeSource())
    result = _run(["-f", "brawl", "--db", db_url])
    assert result.exit_code == 2
    assert "Invalid value" in result.output


def test_db_defaults_to_get_db_url(monkeypatch, db_url):
    monkeypatch.setattr("src.config.get_db_url", lambda: db_url)
    _install(monkeypatch, FakeSource())
    result = _run(["-f", "modern", "--limit", "1"])
    assert result.exit_code == 0, result.output
    assert _count(db_url) == 1


# ── fetcher / --no-cache ────────────────────────────────────────────────────


def test_no_cache_flag_builds_no_cache_fetcher(monkeypatch, db_url):
    seen = []
    real = cli_mod._make_fetcher

    def spy(no_cache):
        seen.append(no_cache)
        return real(no_cache)

    monkeypatch.setattr(cli_mod, "_make_fetcher", spy)
    _install(monkeypatch, FakeSource())
    assert _run(["-f", "modern", "--limit", "1", "--no-cache", "--db", db_url]).exit_code == 0
    assert _run(["-f", "modern", "--limit", "1", "--db", db_url]).exit_code == 0
    assert seen == [True, False]


def test_make_fetcher_no_cache_bypasses_cache_reads(monkeypatch):
    calls = []

    def fake_get_text(self, url, *, ttl_hours=None, use_cache=True):
        calls.append((url, ttl_hours, use_cache))
        return "{}"

    monkeypatch.setattr(PoliteFetcher, "get_text", fake_get_text)
    cached = cli_mod._make_fetcher(False)
    uncached = cli_mod._make_fetcher(True)
    try:
        assert type(cached) is PoliteFetcher
        assert isinstance(uncached, PoliteFetcher)
        cached.get_text("u1", ttl_hours=5)
        uncached.get_text("u2", ttl_hours=5)
        uncached.get_json("u3")
    finally:
        cached.close()
        uncached.close()
    assert calls == [("u1", 5, True), ("u2", 5, False), ("u3", None, False)]

"""Tests for scripts/diagnose_collection_history.py (F176-T01)."""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.diagnose_collection_history import (  # noqa: E402
    EntryNotFoundError,
    candidate_keys,
    collect_entry_diagnosis,
    collect_global_stats,
    main,
    select_entry_ids,
    summarize,
)
from src.database.models import (  # noqa: E402
    Base,
    CardRow,
    PriceObservationRow,
    SourceCardRow,
    UserCollectionRow,
)
from src.database.repository import Repository  # noqa: E402
from src.domain.models import HistoricalPrice  # noqa: E402

TODAY = date.today()


@pytest.fixture
def repo():
    r = Repository(db_url="sqlite:///:memory:")
    Base.metadata.create_all(r.engine)
    return r


def _card(repo: Repository, number: str = "1") -> int:
    with Session(repo.engine) as s:
        row = CardRow(game="mtg", name_en=f"Card {number}", set_code="TST", collector_number=number)
        s.add(row)
        s.commit()
        return row.id


def _entry(
    repo: Repository, card_id: int | None, extras: str | None = None, user_id: str = "u1"
) -> int:
    with Session(repo.engine) as s:
        row = UserCollectionRow(
            user_id=user_id,
            card_id=card_id,
            set_code="TST",
            collector_number="1",
            extras=extras,
        )
        s.add(row)
        s.commit()
        return row.id


def _source_card(repo: Repository, card_id: int, source: str, external_id: str) -> None:
    with Session(repo.engine) as s:
        s.add(
            SourceCardRow(source=source, external_id=external_id, card_id=card_id, url="https://x")
        )
        s.commit()


def _obs(repo: Repository, source: str, external_id: str, days_ago: list[int]) -> None:
    repo.insert_price_observations(
        [
            HistoricalPrice(
                source=source,
                external_id=external_id,
                observed_at=TODAY - timedelta(days=d),
                median_price=Decimal("10.00"),
            )
            for d in days_ago
        ]
    )


def _count_obs(repo: Repository) -> int:
    with Session(repo.engine) as s:
        return s.execute(select(func.count()).select_from(PriceObservationRow)).scalar_one()


class TestCandidateKeys:
    def test_direct_keys_appended_after_source_cards(self):
        keys = candidate_keys(7, [("myp", "myp_99")])
        assert keys == [
            ("myp", "myp_99"),
            ("liga", "liga_7"),
            ("liga", "liga_7_foil"),
            ("manual", "manual_7"),
        ]

    def test_no_duplicates(self):
        keys = candidate_keys(7, [("liga", "liga_7")])
        assert keys.count(("liga", "liga_7")) == 1


class TestCollectEntryDiagnosis:
    def test_liga_only_normal_card_is_invisible_to_endpoint(self, repo):
        card_id = _card(repo)
        entry_id = _entry(repo, card_id)
        _obs(repo, "liga", f"liga_{card_id}", [0, 1, 2])

        d = collect_entry_diagnosis(repo, entry_id, days=30)

        assert d["status"] == "linked"
        assert d["current_endpoint_points"] == 0
        assert d["available_points"] == 3
        assert d["lost_points"] == 3
        assert d["resolver_days"] == 3
        assert d["flags"]["H1"] is True
        assert d["flags"]["H4"] is False

    def test_foil_entry_reports_both_series_and_mixed_variants(self, repo):
        card_id = _card(repo)
        entry_id = _entry(repo, card_id, extras="Foil")
        _obs(repo, "liga", f"liga_{card_id}_foil", [0, 1])
        _obs(repo, "liga", f"liga_{card_id}", [0, 3])

        d = collect_entry_diagnosis(repo, entry_id, days=30)

        ext_ids = {s["external_id"] for s in d["series"]}
        assert ext_ids == {f"liga_{card_id}", f"liga_{card_id}_foil"}
        assert d["is_foil"] is True
        assert d["has_liga_foil"] and d["has_liga_normal"]
        assert d["mixed_variants"] is True
        assert d["flags"]["H4"] is True
        # Resolver keeps only the foil series
        assert d["resolver_days"] == 2

    def test_daily_snapshot_of_myp_source_card_is_lost(self, repo):
        card_id = _card(repo)
        entry_id = _entry(repo, card_id)
        _source_card(repo, card_id, "myp", "myp_123")
        _obs(repo, "myp", "myp_123", [5])
        _obs(repo, "daily_snapshot", "myp_123", [0, 1, 2, 3, 4, 5])

        d = collect_entry_diagnosis(repo, entry_id, days=30)

        assert d["current_endpoint_points"] == 1
        assert d["lost_by_source"] == {"daily_snapshot": 6}
        assert d["flags"]["H2"] is True
        assert d["resolver_days"] == 6

    def test_same_day_liga_and_myp_counts_duplicate(self, repo):
        card_id = _card(repo)
        entry_id = _entry(repo, card_id)
        _source_card(repo, card_id, "myp", "myp_1")
        _obs(repo, "myp", "myp_1", [0])
        _obs(repo, "liga", f"liga_{card_id}", [0])

        d = collect_entry_diagnosis(repo, entry_id, days=30)

        assert d["duplicate_dates"] >= 1
        assert d["flags"]["H5"] is True
        assert d["resolver_days"] == 1

    def test_endpoint_duplicate_dates_from_jsonld(self, repo):
        card_id = _card(repo)
        entry_id = _entry(repo, card_id)
        _source_card(repo, card_id, "myp", "myp_1")
        _obs(repo, "myp", "myp_1", [0])
        _obs(repo, "jsonld_snapshot", "myp_1", [0])

        d = collect_entry_diagnosis(repo, entry_id, days=30)

        assert d["current_endpoint_points"] == 2
        assert d["current_endpoint_duplicate_dates"] == 1
        assert d["lost_points"] == 0

    def test_snapshot_before_first_real_flags_h6(self, repo):
        card_id = _card(repo)
        entry_id = _entry(repo, card_id)
        _obs(repo, "liga", f"liga_{card_id}", [0])
        _obs(repo, "daily_snapshot", f"liga_{card_id}", [0, 1, 2])

        d = collect_entry_diagnosis(repo, entry_id, days=30)

        assert d["snapshots_before_first_real"] == 2
        assert d["flags"]["H6"] is True
        assert d["last_daily_snapshot"] == TODAY.isoformat()

    def test_backfill_snapshots_detected_as_fabricated(self, repo):
        # Legacy (pre-F176) backfill_snapshots wrote daily_snapshot rows dated
        # today..today-4 with the current price; F176-T05 replaced it with a
        # forward-fill under its own source, so seed the legacy rows directly.
        card_id = _card(repo)
        entry_id = _entry(repo, card_id)
        _obs(repo, "liga", f"liga_{card_id}", [20])
        _obs(repo, "daily_snapshot", f"liga_{card_id}", [0, 1, 2, 3, 4])

        d = collect_entry_diagnosis(repo, entry_id, days=30)

        # 5 rows (today..today-4); the 4 dated before today are retroactive
        assert d["backfilled_snapshots"] == 4
        assert d["snapshots_before_first_real"] == 0
        assert d["flags"]["H6"] is True

    def test_daily_snapshot_run_is_not_fabricated(self, repo):
        from src.collectors.price_snapshot import run_daily_snapshot

        card_id = _card(repo)
        entry_id = _entry(repo, card_id)
        _obs(repo, "liga", f"liga_{card_id}", [3])
        run_daily_snapshot(repo)

        d = collect_entry_diagnosis(repo, entry_id, days=30)

        assert d["backfilled_snapshots"] == 0
        assert d["snapshot_days_window"] == 1
        assert d["flags"]["H6"] is False
        assert d["flags"]["H3"] is False

    def test_sparse_real_points_without_snapshot_flags_h3(self, repo):
        card_id = _card(repo)
        entry_id = _entry(repo, card_id)
        _obs(repo, "liga", f"liga_{card_id}", [3])

        d = collect_entry_diagnosis(repo, entry_id, days=30)

        assert d["flags"]["H3"] is True

    def test_window_excludes_old_points(self, repo):
        card_id = _card(repo)
        entry_id = _entry(repo, card_id)
        _obs(repo, "liga", f"liga_{card_id}", [0, 30, 31, 100])

        d = collect_entry_diagnosis(repo, entry_id, days=30)

        # Boundary: cutoff = today - 30 is inclusive, like get_price_series
        assert d["available_points"] == 2
        series = d["series"][0]
        assert series["count"] == 4
        assert series["days_90"] == 3

    def test_unlinked_entry(self, repo):
        entry_id = _entry(repo, None)

        d = collect_entry_diagnosis(repo, entry_id, days=30)

        assert d["status"] == "unlinked"
        assert d["available_points"] == 0
        assert not any(d["flags"].values())

    def test_missing_entry_raises(self, repo):
        with pytest.raises(EntryNotFoundError):
            collect_entry_diagnosis(repo, 999, days=30)


class TestSummarize:
    def test_empty(self):
        s = summarize([])
        assert s["entries"] == 0
        assert s["pct_zero_current_endpoint"] == 0.0
        assert s["pct_resolver_ge2_days"] == 0.0
        assert s["last_daily_snapshot"] is None
        assert s["hypothesis_counts"] == {f"H{i}": 0 for i in range(1, 7)}

    def test_aggregates(self, repo):
        c1, c2 = _card(repo, "1"), _card(repo, "2")
        e1 = _entry(repo, c1)
        e2 = _entry(repo, c2, extras="Foil")
        e3 = _entry(repo, None)
        _obs(repo, "liga", f"liga_{c1}", [0, 1])
        _obs(repo, "liga", f"liga_{c2}_foil", [0])

        diags = [collect_entry_diagnosis(repo, e, 30) for e in (e1, e2, e3)]
        s = summarize(diags)

        assert s["entries"] == 3
        assert s["linked"] == 2
        assert s["unlinked"] == 1
        assert s["pct_zero_current_endpoint"] == 100.0
        assert s["pct_resolver_ge2_days"] == 33.3
        assert s["available_by_source"] == {"liga": 3}
        assert s["foil_entries"] == 1
        assert s["foil_entries_with_liga_foil_series"] == 1
        assert s["hypothesis_counts"]["H1"] == 2


class TestGlobalAndSelection:
    def test_prefix_counts(self, repo):
        _obs(repo, "liga", "liga_1", [0])
        _obs(repo, "liga", "liga_1_foil", [0])
        _obs(repo, "liga", "liga_catalog_TST_1", [0, 1])
        _obs(repo, "manual", "manual_1", [0])
        _obs(repo, "daily_snapshot", "liga_1", [2])

        stats = collect_global_stats(repo, 30)

        assert stats["by_prefix"] == {
            "liga_catalog_%": 2,
            "liga_%_foil": 1,
            "liga_% (normal)": 2,
            "manual_%": 1,
        }
        assert stats["last_daily_snapshot"] == (TODAY - timedelta(days=2)).isoformat()
        assert stats["daily_snapshot_days_in_window"] == 1

    def test_select_entry_ids(self, repo):
        a = _entry(repo, None, user_id="a")
        _entry(repo, None, user_id="b")
        a2 = _entry(repo, None, user_id="a")
        assert select_entry_ids(repo, "a", 10) == [a, a2]
        assert len(select_entry_ids(repo, None, 2)) == 2
        assert select_entry_ids(repo, None, 0) == []


@pytest.fixture
def file_repo(tmp_path):
    url = f"sqlite:///{tmp_path / 't.db'}"
    r = Repository(db_url=url)
    return r, url


class TestMain:
    def test_json_and_text_output_read_only(self, file_repo, tmp_path, capsys):
        repo, url = file_repo
        card_id = _card(repo)
        _entry(repo, card_id)
        _obs(repo, "liga", f"liga_{card_id}", [0, 1, 2])
        before = _count_obs(repo)
        out = tmp_path / "report.json"

        rc = main(["--db", url, "--json", str(out)])

        assert rc == 0
        assert _count_obs(repo) == before
        report = json.loads(out.read_text())
        assert report["summary"]["entries"] == 1
        assert report["entries"][0]["available_points"] == 3
        assert "F176 collection history diagnosis" in capsys.readouterr().out

    def test_missing_entry_exit_1(self, file_repo, capsys):
        _, url = file_repo
        rc = main(["--db", url, "--entry-id", "12345"])
        assert rc == 1
        assert "12345" in capsys.readouterr().err

    def test_sample_zero(self, file_repo, tmp_path):
        repo, url = file_repo
        _entry(repo, None)
        out = tmp_path / "r.json"
        rc = main(["--db", url, "--sample", "0", "--json", str(out)])
        assert rc == 0
        assert json.loads(out.read_text())["summary"]["entries"] == 0

    def test_invalid_days(self, file_repo):
        _, url = file_repo
        assert main(["--db", url, "--days", "0"]) == 2

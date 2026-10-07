"""Tests for collection snapshot on import replace (FIX-01 snapshot mechanism)."""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.collection.importer import import_collection_csv
from src.database.models import Base, CollectionSnapshotRow


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


def _write_csv(tmp_dir: str, header: list[str], rows: list[list[str]]) -> Path:
    path = Path(tmp_dir) / "collection.csv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return path


class TestCollectionSnapshot:
    """Snapshot is created before destructive import replace."""

    def test_snapshot_created_on_reimport(self, engine) -> None:
        """When a user re-imports, a CollectionSnapshotRow is created with correct row_count."""
        with tempfile.TemporaryDirectory() as tmp:
            header = ["Name", "Set code", "Collector number", "Quantity", "Price"]
            rows_v1 = [
                ["Lightning Bolt", "m10", "146", "2", "R$ 10,00"],
                ["Counterspell", "c21", "263", "1", "R$ 2,50"],
            ]
            path = _write_csv(tmp, header, rows_v1)

            # First import -- no snapshot expected
            result1 = import_collection_csv(engine, path, user_id="u1")
            assert result1["imported"] == 2
            assert result1["snapshot_id"] is None

            # Second import -- snapshot should be created
            rows_v2 = [
                ["Swords to Plowshares", "c21", "39", "1", "R$ 5,00"],
            ]
            path2 = _write_csv(tmp, header, rows_v2)
            result2 = import_collection_csv(engine, path2, user_id="u1")
            assert result2["imported"] == 1
            assert result2["snapshot_id"] is not None

            with Session(engine) as session:
                snapshot = session.query(CollectionSnapshotRow).filter_by(user_id="u1").one()
                assert snapshot.row_count == 2
                assert snapshot.reason == "import_replace"

    def test_snapshot_data_is_valid_json(self, engine) -> None:
        """snapshot_data contains valid JSON with expected card entries."""
        with tempfile.TemporaryDirectory() as tmp:
            header = ["Name", "Set code", "Collector number", "Quantity", "Price"]
            rows_v1 = [
                ["Lightning Bolt", "m10", "146", "2", "R$ 10,00"],
                ["Counterspell", "c21", "263", "1", "R$ 2,50"],
                ["Sol Ring", "c21", "266", "4", "R$ 15,00"],
            ]
            path = _write_csv(tmp, header, rows_v1)
            import_collection_csv(engine, path, user_id="u1")

            # Re-import to trigger snapshot
            rows_v2 = [
                ["Swords to Plowshares", "c21", "39", "1", "R$ 5,00"],
            ]
            path2 = _write_csv(tmp, header, rows_v2)
            import_collection_csv(engine, path2, user_id="u1")

            with Session(engine) as session:
                snapshot = session.query(CollectionSnapshotRow).filter_by(user_id="u1").one()
                data = json.loads(snapshot.snapshot_data)
                assert isinstance(data, list)
                assert len(data) == 3

                set_codes = {entry["set_code"] for entry in data}
                assert "m10" in set_codes
                assert "c21" in set_codes

                bolt = next(e for e in data if e["collector_number"] == "146")
                assert bolt["name_en"] == "Lightning Bolt"
                assert bolt["quantity"] == 2
                assert bolt["acquisition_price"] == "10.00"

    def test_no_snapshot_on_first_import(self, engine) -> None:
        """No snapshot is created when there are no existing rows."""
        with tempfile.TemporaryDirectory() as tmp:
            header = ["Name", "Set code", "Collector number", "Quantity"]
            rows = [["Lightning Bolt", "m10", "146", "1"]]
            path = _write_csv(tmp, header, rows)
            result = import_collection_csv(engine, path, user_id="u1")

            assert result["snapshot_id"] is None

            with Session(engine) as session:
                count = session.query(CollectionSnapshotRow).count()
                assert count == 0

    def test_snapshot_per_user_isolation(self, engine) -> None:
        """Snapshot only captures the importing user's rows, not other users."""
        with tempfile.TemporaryDirectory() as tmp:
            header = ["Name", "Set code", "Collector number", "Quantity"]
            rows = [["Lightning Bolt", "m10", "146", "1"]]
            path = _write_csv(tmp, header, rows)

            # Import for user u1
            import_collection_csv(engine, path, user_id="u1")
            # Import for user u2
            import_collection_csv(engine, path, user_id="u2")

            # Re-import for u1 -- snapshot should only have 1 row (u1's)
            result = import_collection_csv(engine, path, user_id="u1")
            assert result["snapshot_id"] is not None

            with Session(engine) as session:
                snapshot = session.query(CollectionSnapshotRow).filter_by(user_id="u1").one()
                assert snapshot.row_count == 1
                data = json.loads(snapshot.snapshot_data)
                assert len(data) == 1

                # u2 should have no snapshot
                u2_snapshots = session.query(CollectionSnapshotRow).filter_by(user_id="u2").count()
                assert u2_snapshots == 0

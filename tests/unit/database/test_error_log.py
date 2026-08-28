"""Tests for ErrorLogRow model and repository methods."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from src.database.models import Base, ErrorLogRow
from src.database.repository import Repository

# ── Helpers ──────────────────────────────────────────────────────────


def _make_error(
    *,
    timestamp: datetime | None = None,
    level: str = "ERROR",
    error_type: str = "ValueError",
    message: str = "something went wrong",
    module: str | None = "src.api.routers.collection",
    **kwargs: object,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "timestamp": timestamp or datetime(2026, 8, 28, 12, 0, 0),
        "level": level,
        "error_type": error_type,
        "message": message,
        "traceback": kwargs.get("traceback"),
        "module": module,
        "function": kwargs.get("function"),
        "line": kwargs.get("line"),
        "request_method": kwargs.get("request_method"),
        "request_path": kwargs.get("request_path"),
        "request_user_id": kwargs.get("request_user_id"),
        "request_id": kwargs.get("request_id"),
        "request_params": kwargs.get("request_params"),
        "extra": kwargs.get("extra"),
    }


@pytest.fixture()
def repo() -> Repository:
    return Repository(db_url="sqlite:///:memory:")


# ── Model tests ──────────────────────────────────────────────────────


class TestErrorLogRowTable:
    """Verify error_log table schema."""

    def test_create_all_creates_error_log_table(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        inspector = inspect(engine)
        assert "error_log" in inspector.get_table_names()

    def test_error_log_has_expected_columns(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("error_log")}
        expected = {
            "id",
            "timestamp",
            "level",
            "error_type",
            "message",
            "traceback",
            "module",
            "function",
            "line",
            "request_method",
            "request_path",
            "request_user_id",
            "request_id",
            "request_params",
            "extra",
        }
        assert expected == columns

    def test_error_log_has_indexes(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        inspector = inspect(engine)
        indexes = inspector.get_indexes("error_log")
        index_names = {idx["name"] for idx in indexes}
        assert "ix_error_log_timestamp" in index_names
        assert "ix_error_log_level" in index_names

    def test_insert_and_read_all_fields(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        now = datetime(2026, 8, 28, 12, 0, 0)
        row = ErrorLogRow(
            id="abc-123",
            timestamp=now,
            level="ERROR",
            error_type="ValueError",
            message="bad input",
            traceback="Traceback ...",
            module="src.api.routers.collection",
            function="get_collection",
            line=42,
            request_method="GET",
            request_path="/api/collection",
            request_user_id=1,
            request_id="req-456",
            request_params='{"page": 1}',
            extra='{"context": "test"}',
        )

        with Session(engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.id == "abc-123"
            assert row.timestamp == now
            assert row.level == "ERROR"
            assert row.error_type == "ValueError"
            assert row.message == "bad input"
            assert row.traceback == "Traceback ..."
            assert row.module == "src.api.routers.collection"
            assert row.function == "get_collection"
            assert row.line == 42
            assert row.request_method == "GET"
            assert row.request_path == "/api/collection"
            assert row.request_user_id == 1
            assert row.request_id == "req-456"
            assert row.request_params == '{"page": 1}'
            assert row.extra == '{"context": "test"}'

    def test_nullable_fields_accept_none(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        row = ErrorLogRow(
            id="def-789",
            timestamp=datetime(2026, 8, 28, 12, 0, 0),
            level="WARNING",
            error_type="DeprecationWarning",
            message="old API usage",
        )

        with Session(engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.traceback is None
            assert row.module is None
            assert row.function is None
            assert row.line is None
            assert row.request_method is None
            assert row.request_path is None
            assert row.request_user_id is None
            assert row.request_id is None
            assert row.request_params is None
            assert row.extra is None


# ── Repository tests ─────────────────────────────────────────────────


class TestInsertErrorLog:
    def test_insert_and_retrieve(self, repo: Repository) -> None:
        entry = _make_error()
        repo.insert_error_log(entry)

        result = repo.get_error_log(entry["id"])
        assert result is not None
        assert result["id"] == entry["id"]
        assert result["level"] == "ERROR"
        assert result["message"] == "something went wrong"


class TestListErrorLogs:
    def test_happy_path_returns_all(self, repo: Repository) -> None:
        for i in range(5):
            repo.insert_error_log(
                _make_error(
                    timestamp=datetime(2026, 8, 28, 12, i, 0),
                    message=f"error {i}",
                )
            )

        results, total = repo.list_error_logs()
        assert total == 5
        assert len(results) == 5

    def test_ordered_by_timestamp_desc(self, repo: Repository) -> None:
        for i in range(3):
            repo.insert_error_log(_make_error(timestamp=datetime(2026, 8, 28, 12, i, 0)))

        results, _ = repo.list_error_logs()
        timestamps = [r["timestamp"] for r in results]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_filter_by_level(self, repo: Repository) -> None:
        repo.insert_error_log(_make_error(level="ERROR"))
        repo.insert_error_log(_make_error(level="WARNING"))
        repo.insert_error_log(_make_error(level="ERROR"))

        results, total = repo.list_error_logs(level="ERROR")
        assert total == 2
        assert all(r["level"] == "ERROR" for r in results)

    def test_filter_by_date_range(self, repo: Repository) -> None:
        repo.insert_error_log(_make_error(timestamp=datetime(2026, 8, 25, 12, 0, 0)))
        repo.insert_error_log(_make_error(timestamp=datetime(2026, 8, 27, 12, 0, 0)))
        repo.insert_error_log(_make_error(timestamp=datetime(2026, 8, 29, 12, 0, 0)))

        results, total = repo.list_error_logs(
            date_from=datetime(2026, 8, 26),
            date_to=datetime(2026, 8, 28),
        )
        assert total == 1
        assert len(results) == 1

    def test_filter_by_module_substring(self, repo: Repository) -> None:
        repo.insert_error_log(_make_error(module="src.api.routers.collection"))
        repo.insert_error_log(_make_error(module="src.api.routers.scans"))
        repo.insert_error_log(_make_error(module="src.collectors.scan"))

        results, total = repo.list_error_logs(module="routers")
        assert total == 2

    def test_pagination(self, repo: Repository) -> None:
        for i in range(10):
            repo.insert_error_log(_make_error(timestamp=datetime(2026, 8, 28, 12, i, 0)))

        results, total = repo.list_error_logs(limit=3, offset=0)
        assert total == 10
        assert len(results) == 3

        results2, total2 = repo.list_error_logs(limit=3, offset=3)
        assert total2 == 10
        assert len(results2) == 3
        # No overlap
        ids1 = {r["id"] for r in results}
        ids2 = {r["id"] for r in results2}
        assert ids1.isdisjoint(ids2)


class TestGetErrorLog:
    def test_returns_entry_by_id(self, repo: Repository) -> None:
        entry = _make_error(
            traceback="Traceback (most recent call last)...",
            function="handle_request",
            line=99,
        )
        repo.insert_error_log(entry)

        result = repo.get_error_log(entry["id"])
        assert result is not None
        assert result["error_type"] == "ValueError"
        assert result["traceback"] == "Traceback (most recent call last)..."
        assert result["function"] == "handle_request"
        assert result["line"] == 99

    def test_returns_none_for_missing(self, repo: Repository) -> None:
        result = repo.get_error_log("nonexistent-id")
        assert result is None


class TestDeleteErrorLogsBefore:
    def test_deletes_old_entries(self, repo: Repository) -> None:
        cutoff = datetime(2026, 8, 27, 0, 0, 0)

        # Old entries
        for i in range(3):
            repo.insert_error_log(_make_error(timestamp=datetime(2026, 8, 25, i, 0, 0)))
        # New entries
        for i in range(2):
            repo.insert_error_log(_make_error(timestamp=datetime(2026, 8, 28, i, 0, 0)))

        deleted = repo.delete_error_logs_before(cutoff)
        assert deleted == 3

        results, total = repo.list_error_logs()
        assert total == 2

    def test_deletes_nothing_when_all_newer(self, repo: Repository) -> None:
        repo.insert_error_log(_make_error(timestamp=datetime(2026, 8, 28, 12, 0, 0)))

        deleted = repo.delete_error_logs_before(datetime(2026, 8, 1))
        assert deleted == 0


class TestDeleteErrorLogsExcess:
    def test_keeps_n_newest(self, repo: Repository) -> None:
        for i in range(15):
            repo.insert_error_log(_make_error(timestamp=datetime(2026, 8, 28, 0, i, 0)))

        deleted = repo.delete_error_logs_excess(max_entries=10)
        assert deleted == 5

        results, total = repo.list_error_logs(limit=100)
        assert total == 10
        # Verify these are the 10 newest (minutes 5..14)
        timestamps = [r["timestamp"] for r in results]
        oldest_kept = min(timestamps)
        assert oldest_kept == datetime(2026, 8, 28, 0, 5, 0)

    def test_no_op_when_under_limit(self, repo: Repository) -> None:
        for i in range(3):
            repo.insert_error_log(_make_error(timestamp=datetime(2026, 8, 28, 0, i, 0)))

        deleted = repo.delete_error_logs_excess(max_entries=10)
        assert deleted == 0

        _, total = repo.list_error_logs()
        assert total == 3

    def test_no_op_when_exactly_at_limit(self, repo: Repository) -> None:
        for i in range(5):
            repo.insert_error_log(_make_error(timestamp=datetime(2026, 8, 28, 0, i, 0)))

        deleted = repo.delete_error_logs_excess(max_entries=5)
        assert deleted == 0

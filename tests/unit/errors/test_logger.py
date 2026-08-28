"""Tests for src/errors/logger.py — ErrorLogger service."""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock

from src.errors.logger import (
    ErrorLogger,
    get_global_error_logger,
    make_db_sink,
    make_jsonl_sink,
    set_global_error_logger,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_list_sink() -> tuple[list[dict], callable]:
    """Return (collected_list, sink_fn)."""
    collected: list[dict] = []

    def sink(error_dict: dict) -> None:
        collected.append(error_dict)

    return collected, sink


def _raise_value_error(msg: str = "boom") -> None:
    """Raise a ValueError so we get a real traceback."""
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestCaptureHappyPath:
    def test_capture_returns_all_fields(self):
        collected, sink = _make_list_sink()
        logger = ErrorLogger(sinks=[sink])

        try:
            _raise_value_error("test error")
        except ValueError as exc:
            error_id = logger.capture(exc)

        assert len(collected) == 1
        d = collected[0]

        # All expected keys present
        expected_keys = {
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
        assert set(d.keys()) == expected_keys

        assert d["id"] == error_id
        assert d["level"] == "ERROR"
        assert d["error_type"] == "ValueError"
        assert d["message"] == "test error"
        assert "ValueError: test error" in d["traceback"]
        assert d["module"] is not None
        assert d["function"] is not None
        assert d["line"] is not None
        assert d["extra"] is None

    def test_capture_with_extra(self):
        collected, sink = _make_list_sink()
        logger = ErrorLogger(sinks=[sink])

        try:
            _raise_value_error()
        except ValueError as exc:
            logger.capture(exc, extra={"card_id": 42})

        d = collected[0]
        assert json.loads(d["extra"]) == {"card_id": 42}


# ---------------------------------------------------------------------------
# UUID format
# ---------------------------------------------------------------------------


class TestUuidFormat:
    def test_capture_returns_valid_uuid(self):
        collected, sink = _make_list_sink()
        logger = ErrorLogger(sinks=[sink])

        try:
            _raise_value_error()
        except ValueError as exc:
            error_id = logger.capture(exc)

        # Should not raise
        parsed = uuid.UUID(error_id)
        assert str(parsed) == error_id

    def test_warning_returns_valid_uuid(self):
        collected, sink = _make_list_sink()
        logger = ErrorLogger(sinks=[sink])

        error_id = logger.capture_warning("something odd")
        parsed = uuid.UUID(error_id)
        assert str(parsed) == error_id


# ---------------------------------------------------------------------------
# Request context
# ---------------------------------------------------------------------------


class TestRequestContext:
    def test_request_context_fields_appear(self):
        collected, sink = _make_list_sink()
        logger = ErrorLogger(sinks=[sink])

        ctx = {
            "request_method": "POST",
            "request_path": "/api/scan",
            "request_user_id": "user-123",
            "request_id": "req-abc",
            "params": {"card_id": 7},
        }

        try:
            _raise_value_error()
        except ValueError as exc:
            logger.capture(exc, request_context=ctx)

        d = collected[0]
        assert d["request_method"] == "POST"
        assert d["request_path"] == "/api/scan"
        assert d["request_user_id"] == "user-123"
        assert d["request_id"] == "req-abc"
        assert json.loads(d["request_params"]) == {"card_id": 7}

    def test_partial_request_context(self):
        collected, sink = _make_list_sink()
        logger = ErrorLogger(sinks=[sink])

        try:
            _raise_value_error()
        except ValueError as exc:
            logger.capture(exc, request_context={"request_method": "GET"})

        d = collected[0]
        assert d["request_method"] == "GET"
        assert d["request_path"] is None
        assert d["request_params"] is None


# ---------------------------------------------------------------------------
# Warning
# ---------------------------------------------------------------------------


class TestCaptureWarning:
    def test_warning_level_and_no_traceback(self):
        collected, sink = _make_list_sink()
        logger = ErrorLogger(sinks=[sink])

        error_id = logger.capture_warning("disk almost full", module="src.collectors.scan")

        assert len(collected) == 1
        d = collected[0]
        assert d["id"] == error_id
        assert d["level"] == "WARNING"
        assert d["error_type"] == "Warning"
        assert d["message"] == "disk almost full"
        assert d["traceback"] is None
        assert d["module"] == "src.collectors.scan"
        assert d["function"] is None
        assert d["line"] is None

    def test_warning_with_extra(self):
        collected, sink = _make_list_sink()
        logger = ErrorLogger(sinks=[sink])

        logger.capture_warning("slow query", extra={"duration_ms": 5200})

        d = collected[0]
        assert json.loads(d["extra"]) == {"duration_ms": 5200}


# ---------------------------------------------------------------------------
# Sink failure isolation
# ---------------------------------------------------------------------------


class TestSinkFailure:
    def test_failing_sink_does_not_block_other_sinks(self):
        collected_good, good_sink = _make_list_sink()

        def bad_sink(error_dict: dict) -> None:
            raise RuntimeError("sink exploded")

        logger = ErrorLogger(sinks=[bad_sink, good_sink])

        try:
            _raise_value_error()
        except ValueError as exc:
            logger.capture(exc)

        # Good sink still received the error
        assert len(collected_good) == 1
        assert collected_good[0]["error_type"] == "ValueError"

    def test_all_sinks_failing_does_not_raise(self):
        def bad1(d: dict) -> None:
            raise RuntimeError("bad1")

        def bad2(d: dict) -> None:
            raise RuntimeError("bad2")

        logger = ErrorLogger(sinks=[bad1, bad2])

        try:
            _raise_value_error()
        except ValueError as exc:
            # Should not raise
            error_id = logger.capture(exc)

        assert error_id is not None


# ---------------------------------------------------------------------------
# JSONL sink
# ---------------------------------------------------------------------------


class TestJsonlSink:
    def test_jsonl_writes_valid_lines(self, tmp_path):
        file_path = str(tmp_path / "errors.jsonl")
        sink = make_jsonl_sink(file_path)
        logger = ErrorLogger(sinks=[sink])

        for i in range(3):
            try:
                raise ValueError(f"error {i}")
            except ValueError as exc:
                logger.capture(exc)

        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 3
        for line in lines:
            parsed = json.loads(line)
            assert "id" in parsed
            assert parsed["error_type"] == "ValueError"

    def test_jsonl_creates_parent_dirs(self, tmp_path):
        file_path = str(tmp_path / "nested" / "dir" / "errors.jsonl")
        sink = make_jsonl_sink(file_path)
        logger = ErrorLogger(sinks=[sink])

        try:
            _raise_value_error()
        except ValueError as exc:
            logger.capture(exc)

        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1


# ---------------------------------------------------------------------------
# DB sink
# ---------------------------------------------------------------------------


class TestDbSink:
    def test_db_sink_calls_repo(self):
        repo = MagicMock()
        sink = make_db_sink(repo)
        logger = ErrorLogger(sinks=[sink])

        try:
            _raise_value_error()
        except ValueError as exc:
            logger.capture(exc)

        repo.insert_error_log.assert_called_once()
        call_dict = repo.insert_error_log.call_args[0][0]
        assert call_dict["error_type"] == "ValueError"
        # Timestamp should be converted from string to datetime
        from datetime import datetime

        assert isinstance(call_dict["timestamp"], datetime)


# ---------------------------------------------------------------------------
# Traceback extraction
# ---------------------------------------------------------------------------


class TestTracebackExtraction:
    def test_module_function_line_match_raise_site(self):
        collected, sink = _make_list_sink()
        logger = ErrorLogger(sinks=[sink])

        try:
            _raise_value_error("trace test")
        except ValueError as exc:
            logger.capture(exc)

        d = collected[0]
        # The innermost frame should be _raise_value_error
        assert d["function"] == "_raise_value_error"
        assert d["module"] is not None
        assert isinstance(d["line"], int)
        assert d["line"] > 0

    def test_nested_call_traceback(self):
        collected, sink = _make_list_sink()
        logger = ErrorLogger(sinks=[sink])

        def inner():
            raise TypeError("inner fail")

        def outer():
            inner()

        try:
            outer()
        except TypeError as exc:
            logger.capture(exc)

        d = collected[0]
        # Innermost frame is inner()
        assert d["function"] == "inner"
        assert d["error_type"] == "TypeError"

    def test_no_traceback_on_synthetic_exception(self):
        """Exception created without raise has no __traceback__."""
        collected, sink = _make_list_sink()
        logger = ErrorLogger(sinks=[sink])

        exc = RuntimeError("synthetic")
        logger.capture(exc)

        d = collected[0]
        assert d["module"] is None
        assert d["function"] is None
        assert d["line"] is None
        assert d["error_type"] == "RuntimeError"


# ---------------------------------------------------------------------------
# Global logger
# ---------------------------------------------------------------------------


class TestGlobalLogger:
    def test_set_and_get_global_logger(self):
        logger = ErrorLogger(sinks=[])
        set_global_error_logger(logger)
        assert get_global_error_logger() is logger

        # Cleanup
        set_global_error_logger(None)
        assert get_global_error_logger() is None

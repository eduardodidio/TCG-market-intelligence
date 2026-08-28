"""Structured error logger with pluggable sinks."""

from __future__ import annotations

import json
import threading
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timezone

import structlog

log = structlog.get_logger()

# Global logger instance (set in app lifespan, used by non-request contexts)
_global_logger: ErrorLogger | None = None


def set_global_error_logger(logger: ErrorLogger) -> None:
    global _global_logger
    _global_logger = logger


def get_global_error_logger() -> ErrorLogger | None:
    return _global_logger


class ErrorLogger:
    """Captures exceptions and dispatches to pluggable sinks."""

    def __init__(self, sinks: list[Callable[[dict], None]]) -> None:
        self._sinks = sinks

    def capture(
        self,
        exc: BaseException,
        *,
        level: str = "ERROR",
        request_context: dict | None = None,
        extra: dict | None = None,
    ) -> str:
        """Capture an exception. Returns the error ID (UUID)."""
        error_id = str(uuid.uuid4())

        # Extract traceback info
        tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

        # Extract module/function/line from innermost frame
        module_name = None
        func_name = None
        line_no = None
        tb = exc.__traceback__
        if tb is not None:
            # Walk to innermost frame
            while tb.tb_next is not None:
                tb = tb.tb_next
            frame = tb.tb_frame
            module_name = frame.f_globals.get("__name__", frame.f_code.co_filename)
            func_name = frame.f_code.co_name
            line_no = tb.tb_lineno

        error_dict = {
            "id": error_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "error_type": type(exc).__name__,
            "message": str(exc),
            "traceback": tb_str,
            "module": module_name,
            "function": func_name,
            "line": line_no,
            "request_method": None,
            "request_path": None,
            "request_user_id": None,
            "request_id": None,
            "request_params": None,
            "extra": json.dumps(extra) if extra else None,
        }

        # Merge request context if provided
        if request_context:
            for key in ("request_method", "request_path", "request_user_id", "request_id"):
                if key in request_context:
                    error_dict[key] = request_context[key]
            if "params" in request_context:
                error_dict["request_params"] = json.dumps(request_context["params"])

        self._dispatch(error_dict)
        return error_id

    def capture_warning(
        self,
        message: str,
        *,
        module: str | None = None,
        extra: dict | None = None,
    ) -> str:
        """Capture a warning (no exception/traceback)."""
        error_id = str(uuid.uuid4())
        error_dict = {
            "id": error_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "WARNING",
            "error_type": "Warning",
            "message": message,
            "traceback": None,
            "module": module,
            "function": None,
            "line": None,
            "request_method": None,
            "request_path": None,
            "request_user_id": None,
            "request_id": None,
            "request_params": None,
            "extra": json.dumps(extra) if extra else None,
        }
        self._dispatch(error_dict)
        return error_id

    def _dispatch(self, error_dict: dict) -> None:
        """Send to all sinks. Never raises."""
        for sink in self._sinks:
            try:
                sink(error_dict)
            except Exception:
                log.warning("error_logger.sink_failed", sink=str(sink), exc_info=True)


def make_db_sink(repo) -> Callable[[dict], None]:
    """Create a sink that inserts into the error_log table."""

    def sink(error_dict: dict) -> None:
        # Convert ISO timestamp string to datetime for SQLAlchemy
        d = dict(error_dict)
        if isinstance(d.get("timestamp"), str):
            d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        repo.insert_error_log(d)

    return sink


def make_jsonl_sink(file_path: str) -> Callable[[dict], None]:
    """Create a sink that appends JSON lines to a file."""
    lock = threading.Lock()

    def sink(error_dict: dict) -> None:
        import os

        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        line = json.dumps(error_dict, ensure_ascii=False) + "\n"
        with lock:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(line)

    return sink

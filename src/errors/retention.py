"""Retention cleanup for error logs (JSONL files and database)."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

import structlog

log = structlog.get_logger()


def cleanup_jsonl(file_path: str, max_age_days: int, max_entries: int) -> int:
    """Remove old/excess entries from a JSONL error log file.

    Returns the number of entries removed.
    """
    if not os.path.exists(file_path):
        return 0

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return 0

    original_count = len(lines)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    # Parse and filter by age
    entries: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts >= cutoff:
                entries.append(entry)
        except (json.JSONDecodeError, KeyError, ValueError):
            # Keep malformed entries (don't silently drop data)
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                # Truly unparseable line — still keep as raw wrapper
                entries.append({"_raw": line})

    # Sort by timestamp descending, keep only max_entries newest
    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    if len(entries) > max_entries:
        entries = entries[:max_entries]

    removed = original_count - len(entries)

    if removed > 0:
        # Write atomically: tmp file then rename
        dir_name = os.path.dirname(file_path) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".jsonl.tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            os.replace(tmp_path, file_path)
        except Exception:
            # Clean up tmp file on failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    log.info(
        "retention.jsonl_cleanup",
        original=original_count,
        kept=len(entries),
        removed=removed,
    )
    return removed


def cleanup_db(repo, max_age_days: int, max_entries: int) -> int:
    """Run retention cleanup on the error_log database table.

    Returns total number of entries removed.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    removed_by_age = repo.delete_error_logs_before(before=cutoff)
    removed_by_excess = repo.delete_error_logs_excess(max_entries=max_entries)

    total = removed_by_age + removed_by_excess
    log.info(
        "retention.db_cleanup",
        by_age=removed_by_age,
        by_excess=removed_by_excess,
        total=total,
    )
    return total

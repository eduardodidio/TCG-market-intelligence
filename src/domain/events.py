"""Scan event domain model for SSE streaming (F32)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass
class ScanEvent:
    """Event emitted by the scan orchestrator for real-time progress."""

    event_type: str  # "scan_started" | "card_scanned" | "scan_complete"
    scan_id: int
    timestamp: str  # ISO 8601
    # Per-card fields (None for scan_started/scan_complete)
    external_id: str | None = None
    card_name: str | None = None
    price_found: bool = False
    price: Decimal | None = None
    currency: str | None = None
    error: str | None = None
    # Running totals
    cards_processed: int = 0
    cards_total: int = 0
    cards_failed: int = 0
    observations_saved: int = 0

    def to_sse_json(self) -> str:
        """Serialize to a JSON string suitable for SSE ``data:`` lines.

        Decimal values are converted to float for JSON compatibility.
        """
        d = asdict(self)
        if d["price"] is not None:
            d["price"] = float(d["price"])
        return json.dumps(d)

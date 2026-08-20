from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.schemas.collection import SnapshotRequest

# ---------------------------------------------------------------------------
# SnapshotRequest tests
# ---------------------------------------------------------------------------


class TestSnapshotRequest:
    def test_defaults(self) -> None:
        req = SnapshotRequest()
        assert req.limit is None
        assert req.dry_run is False

    def test_with_values(self) -> None:
        req = SnapshotRequest(limit=50, dry_run=True)
        assert req.limit == 50
        assert req.dry_run is True

    def test_limit_positive(self) -> None:
        req = SnapshotRequest(limit=1)
        assert req.limit == 1

    def test_limit_zero_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SnapshotRequest(limit=0)
        assert "limit" in str(exc_info.value).lower()

    def test_limit_negative_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SnapshotRequest(limit=-5)
        assert "limit" in str(exc_info.value).lower()

    def test_json_roundtrip(self) -> None:
        req = SnapshotRequest(limit=25, dry_run=True)
        dumped = req.model_dump()
        restored = SnapshotRequest.model_validate(dumped)
        assert restored.limit == 25
        assert restored.dry_run is True

    def test_json_roundtrip_defaults(self) -> None:
        req = SnapshotRequest()
        dumped = req.model_dump()
        restored = SnapshotRequest.model_validate(dumped)
        assert restored.limit is None
        assert restored.dry_run is False

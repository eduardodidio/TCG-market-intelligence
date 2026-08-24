"""Unit tests for BulkCanonizeResult schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.schemas.collection import BulkCanonizeResult


class TestBulkCanonizeResultSchema:
    """BulkCanonizeResult has all required fields."""

    def test_canonize_all_schema_validation(self):
        result = BulkCanonizeResult(
            total=10,
            canonized=7,
            failed=2,
            skipped=0,
            rate_limited=1,
        )
        assert result.total == 10
        assert result.canonized == 7
        assert result.failed == 2
        assert result.skipped == 0
        assert result.rate_limited == 1

    def test_schema_requires_all_fields(self):
        with pytest.raises(ValidationError):
            BulkCanonizeResult(total=10, canonized=7)

    def test_schema_serializes_to_dict(self):
        result = BulkCanonizeResult(
            total=5,
            canonized=3,
            failed=1,
            skipped=0,
            rate_limited=1,
        )
        d = result.model_dump()
        assert set(d.keys()) == {"total", "canonized", "failed", "skipped", "rate_limited"}

    def test_schema_from_zero_values(self):
        result = BulkCanonizeResult(
            total=0,
            canonized=0,
            failed=0,
            skipped=0,
            rate_limited=0,
        )
        assert result.total == 0

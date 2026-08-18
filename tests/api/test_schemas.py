from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.api.schemas.cards import (
    CardDetail,
    CardListParams,
    CardSummary,
    HistoryParams,
    PriceObservation,
    SourceCardSchema,
)
from src.api.schemas.collect import BackfillRequest, JobStatus, UpdateRequest
from src.api.schemas.envelope import (
    ApiResponse,
    ErrorDetail,
    Meta,
    error_response,
    paginated_response,
    success_response,
)
from src.api.schemas.market import MarketStats, MoverEntry, MoversResponse
from src.api.schemas.sets import SetSummary

# ---------------------------------------------------------------------------
# Envelope tests
# ---------------------------------------------------------------------------


class TestEnvelope:
    def test_success_response(self) -> None:
        resp = success_response(data={"key": "value"})
        assert resp.data == {"key": "value"}
        assert resp.errors == []
        assert resp.meta.request_id is not None

    def test_error_response(self) -> None:
        err = ErrorDetail(code="NOT_FOUND", message="Card not found")
        resp = error_response(errors=[err])
        assert resp.data is None
        assert len(resp.errors) == 1
        assert resp.errors[0].code == "NOT_FOUND"

    def test_error_detail_with_field(self) -> None:
        err = ErrorDetail(code="VALIDATION", message="Invalid value", field="limit")
        assert err.field == "limit"

    def test_paginated_response(self) -> None:
        items = [1, 2, 3]
        resp = paginated_response(data=items, cursor="abc123", total=100)
        assert resp.data == items
        assert resp.meta.cursor == "abc123"
        assert resp.meta.total == 100

    def test_paginated_response_no_cursor(self) -> None:
        resp = paginated_response(data=[], cursor=None, total=0)
        assert resp.meta.cursor is None
        assert resp.meta.total == 0

    def test_request_id_is_uuid_format(self) -> None:
        meta = Meta()
        # Should not raise — valid UUID
        parsed = uuid.UUID(meta.request_id)
        assert str(parsed) == meta.request_id

    def test_request_id_unique_per_instance(self) -> None:
        m1 = Meta()
        m2 = Meta()
        assert m1.request_id != m2.request_id

    def test_api_response_generic_typed(self) -> None:
        resp: ApiResponse[list[int]] = ApiResponse(data=[1, 2, 3])
        assert resp.data == [1, 2, 3]


# ---------------------------------------------------------------------------
# Card schema tests
# ---------------------------------------------------------------------------


class TestCardSchemas:
    def test_card_summary_from_attributes(self) -> None:
        orm_obj = SimpleNamespace(
            id=1,
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="A25",
            collector_number="141",
            latest_price=Decimal("3.50"),
        )
        card = CardSummary.model_validate(orm_obj, from_attributes=True)
        assert card.id == 1
        assert card.name_en == "Lightning Bolt"
        assert card.latest_price == Decimal("3.50")

    def test_card_summary_optional_fields(self) -> None:
        card = CardSummary(id=1, game="magic", name_en="Test Card")
        assert card.name_pt is None
        assert card.set_code is None
        assert card.latest_price is None

    def test_source_card_from_attributes(self) -> None:
        orm_obj = SimpleNamespace(
            source="myp",
            external_id="12345",
            sku="magic_a25_141",
            url="https://example.com/card/12345",
        )
        sc = SourceCardSchema.model_validate(orm_obj, from_attributes=True)
        assert sc.source == "myp"
        assert sc.external_id == "12345"

    def test_card_detail_with_source_cards(self) -> None:
        now = datetime(2025, 1, 1, 12, 0, 0)
        detail = CardDetail(
            id=1,
            game="magic",
            name_en="Lightning Bolt",
            source_cards=[
                SourceCardSchema(
                    source="myp",
                    external_id="123",
                    url="https://example.com/123",
                )
            ],
            created_at=now,
            updated_at=now,
        )
        assert len(detail.source_cards) == 1
        assert detail.source_cards[0].source == "myp"

    def test_price_observation_defaults(self) -> None:
        obs = PriceObservation(observed_at=date(2025, 6, 1))
        assert obs.currency == "BRL"
        assert obs.median_price is None

    def test_price_observation_full(self) -> None:
        obs = PriceObservation(
            observed_at=date(2025, 6, 1),
            median_price=Decimal("10.50"),
            tcg_price=Decimal("11.00"),
            last_sold_price=Decimal("9.75"),
            quantity_available=42,
            currency="BRL",
        )
        assert obs.median_price == Decimal("10.50")
        assert obs.quantity_available == 42


# ---------------------------------------------------------------------------
# CardListParams tests
# ---------------------------------------------------------------------------


class TestCardListParams:
    def test_defaults(self) -> None:
        params = CardListParams()
        assert params.game is None
        assert params.set is None
        assert params.name is None
        assert params.cursor is None
        assert params.limit == 50

    def test_limit_too_high(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            CardListParams(limit=201)
        assert "limit" in str(exc_info.value).lower()

    def test_limit_zero(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            CardListParams(limit=0)
        assert "limit" in str(exc_info.value).lower()

    def test_limit_negative(self) -> None:
        with pytest.raises(ValidationError):
            CardListParams(limit=-1)

    def test_limit_boundary_values(self) -> None:
        p1 = CardListParams(limit=1)
        assert p1.limit == 1
        p200 = CardListParams(limit=200)
        assert p200.limit == 200

    def test_set_alias(self) -> None:
        params = CardListParams(set="DMR")
        assert params.set == "DMR"


# ---------------------------------------------------------------------------
# HistoryParams tests
# ---------------------------------------------------------------------------


class TestHistoryParams:
    def test_default_period(self) -> None:
        params = HistoryParams()
        assert params.period == "90d"

    @pytest.mark.parametrize("period", ["30d", "90d", "180d", "1y", "3y"])
    def test_valid_periods(self, period: str) -> None:
        params = HistoryParams(period=period)
        assert params.period == period

    @pytest.mark.parametrize("period", ["7d", "60d", "2y", "all", "abc", ""])
    def test_invalid_periods(self, period: str) -> None:
        with pytest.raises(ValidationError):
            HistoryParams(period=period)


# ---------------------------------------------------------------------------
# Decimal serialization round-trip
# ---------------------------------------------------------------------------


class TestDecimalRoundTrip:
    def test_card_summary_decimal_roundtrip(self) -> None:
        card = CardSummary(
            id=1,
            game="magic",
            name_en="Test",
            latest_price=Decimal("123.45"),
        )
        dumped = card.model_dump()
        restored = CardSummary.model_validate(dumped)
        assert restored.latest_price == Decimal("123.45")
        assert isinstance(restored.latest_price, Decimal)

    def test_mover_entry_decimal_roundtrip(self) -> None:
        entry = MoverEntry(
            card_id=1,
            name_en="Test",
            price_start=Decimal("10.00"),
            price_end=Decimal("15.50"),
            change_pct=Decimal("55.00"),
        )
        dumped = entry.model_dump()
        restored = MoverEntry.model_validate(dumped)
        assert restored.price_start == Decimal("10.00")
        assert restored.price_end == Decimal("15.50")
        assert restored.change_pct == Decimal("55.00")

    def test_market_stats_decimal_roundtrip(self) -> None:
        stats = MarketStats(
            total_cards=100,
            total_observations=5000,
            avg_price=Decimal("42.99"),
            date_range_start=date(2025, 1, 1),
            date_range_end=date(2025, 6, 1),
        )
        dumped = stats.model_dump()
        restored = MarketStats.model_validate(dumped)
        assert restored.avg_price == Decimal("42.99")

    def test_price_observation_decimal_roundtrip(self) -> None:
        obs = PriceObservation(
            observed_at=date(2025, 6, 1),
            median_price=Decimal("7.25"),
            tcg_price=Decimal("8.00"),
        )
        dumped = obs.model_dump()
        restored = PriceObservation.model_validate(dumped)
        assert restored.median_price == Decimal("7.25")


# ---------------------------------------------------------------------------
# Sets schema tests
# ---------------------------------------------------------------------------


class TestSetSummary:
    def test_construction(self) -> None:
        s = SetSummary(set_code="DMR", game="magic", card_count=261)
        assert s.set_code == "DMR"
        assert s.card_count == 261


# ---------------------------------------------------------------------------
# Market schema tests
# ---------------------------------------------------------------------------


class TestMarketSchemas:
    def test_movers_response_defaults(self) -> None:
        resp = MoversResponse()
        assert resp.gainers == []
        assert resp.losers == []

    def test_movers_response_with_entries(self) -> None:
        entry = MoverEntry(
            card_id=1,
            name_en="Test",
            price_start=Decimal("5.00"),
            price_end=Decimal("10.00"),
            change_pct=Decimal("100.00"),
        )
        resp = MoversResponse(gainers=[entry])
        assert len(resp.gainers) == 1

    def test_market_stats_optional_fields(self) -> None:
        stats = MarketStats(total_cards=0, total_observations=0)
        assert stats.avg_price is None
        assert stats.date_range_start is None


# ---------------------------------------------------------------------------
# Collect schema tests
# ---------------------------------------------------------------------------


class TestCollectSchemas:
    def test_backfill_request_requires_set(self) -> None:
        with pytest.raises(ValidationError):
            BackfillRequest()

    def test_backfill_request_valid(self) -> None:
        req = BackfillRequest(set="DMR")
        assert req.set == "DMR"
        assert req.history_days == 1095
        assert req.limit is None

    def test_backfill_request_with_limit(self) -> None:
        req = BackfillRequest(set="A25", limit=10, history_days=365)
        assert req.limit == 10
        assert req.history_days == 365

    def test_update_request_defaults(self) -> None:
        req = UpdateRequest()
        assert req.set is None

    def test_job_status(self) -> None:
        job = JobStatus(job_id="abc-123", status="running", message="Processing...")
        assert job.job_id == "abc-123"
        assert job.status == "running"

"""F176-T04 — PriceHistoryMeta, CollectionHistoryResponse.meta, PriceObservation.source."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.analytics.aggregation import aggregate_weekly
from src.api.schemas.cards import PriceChangeSummary, PriceObservation
from src.api.schemas.collection import CollectionHistoryResponse, PriceHistoryMeta


class TestPriceHistoryMeta:
    def test_happy_path_serializes_iso_dates(self):
        meta = PriceHistoryMeta(
            variant="foil",
            sources=["liga"],
            first_observed_at=date(2026, 1, 5),
            last_observed_at=date(2026, 9, 20),
            real_points=3,
            snapshot_points=2,
        )
        assert meta.model_dump(mode="json") == {
            "variant": "foil",
            "sources": ["liga"],
            "first_observed_at": "2026-01-05",
            "last_observed_at": "2026-09-20",
            "real_points": 3,
            "snapshot_points": 2,
        }

    def test_defaults(self):
        meta = PriceHistoryMeta(variant="normal")
        assert meta.sources == []
        assert meta.first_observed_at is None
        assert meta.last_observed_at is None
        assert meta.real_points == 0
        assert meta.snapshot_points == 0

    def test_sources_default_not_shared(self):
        a = PriceHistoryMeta(variant="normal")
        a.sources.append("liga")
        assert PriceHistoryMeta(variant="normal").sources == []

    @pytest.mark.parametrize("variant", ["etched", "FOIL", "", None])
    def test_invalid_variant_rejected(self, variant):
        with pytest.raises(ValidationError):
            PriceHistoryMeta(variant=variant)

    def test_variant_required(self):
        with pytest.raises(ValidationError):
            PriceHistoryMeta()

    def test_boundary_zero_points_and_no_dates(self):
        meta = PriceHistoryMeta(
            variant="normal", real_points=0, snapshot_points=0, first_observed_at=None
        )
        assert meta.model_dump(mode="json")["first_observed_at"] is None

    def test_date_parsed_from_iso_string(self):
        meta = PriceHistoryMeta(variant="foil", first_observed_at="2026-02-01")
        assert meta.first_observed_at == date(2026, 2, 1)


class TestCollectionHistoryResponse:
    def test_default_has_null_meta(self):
        resp = CollectionHistoryResponse()
        assert resp.meta is None
        assert resp.observations == []
        assert resp.summary is None

    def test_legacy_construction_serializes_meta_null(self):
        obs = PriceObservation(observed_at=date(2026, 9, 1), median_price=Decimal("10.50"))
        summary = PriceChangeSummary(period="30d", price_start=10.5, price_end=10.5, data_points=1)
        resp = CollectionHistoryResponse(observations=[obs], summary=summary)
        dumped = resp.model_dump(mode="json")
        assert dumped["meta"] is None
        assert dumped["observations"][0]["source"] is None
        assert dumped["observations"][0]["observed_at"] == "2026-09-01"
        assert dumped["summary"]["period"] == "30d"

    def test_with_meta(self):
        resp = CollectionHistoryResponse(
            meta=PriceHistoryMeta(variant="normal", sources=["liga", "myp"], real_points=1)
        )
        dumped = resp.model_dump(mode="json")
        assert dumped["meta"]["variant"] == "normal"
        assert dumped["meta"]["sources"] == ["liga", "myp"]

    def test_meta_from_dict(self):
        resp = CollectionHistoryResponse.model_validate({"meta": {"variant": "foil"}})
        assert isinstance(resp.meta, PriceHistoryMeta)

    def test_meta_invalid_variant_from_dict(self):
        with pytest.raises(ValidationError):
            CollectionHistoryResponse.model_validate({"meta": {"variant": "etched"}})


class TestPriceObservationSource:
    def test_source_defaults_to_none(self):
        obs = PriceObservation(observed_at=date(2026, 9, 1), median_price=Decimal("5"))
        assert obs.source is None

    def test_source_set(self):
        obs = PriceObservation(
            observed_at=date(2026, 9, 1), median_price=Decimal("5"), source="daily_snapshot"
        )
        assert obs.model_dump(mode="json")["source"] == "daily_snapshot"

    def test_aggregate_weekly_still_works(self):
        observations = [
            PriceObservation(
                observed_at=date(2026, 9, d), median_price=Decimal(str(d)), source="liga"
            )
            for d in (7, 8, 9, 14, 15)
        ]
        weekly = aggregate_weekly(observations)
        assert len(weekly) == 2
        assert all(isinstance(o, PriceObservation) for o in weekly)

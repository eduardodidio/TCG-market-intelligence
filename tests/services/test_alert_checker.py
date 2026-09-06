"""Tests for the alert checker service (F106-T02)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.database.models import (
    AlertNotificationRow,
    CardRow,
    PriceAlertRow,
    PriceObservationRow,
    SourceCardRow,
)
from src.database.repository import Repository
from src.domain.models import ScanRun
from src.services.alert_checker import (
    check_alerts_after_scan,
    check_alerts_for_card,
    make_alert_checker_hook,
)


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_alert_checker.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def setup_data(repo):
    """Create test user, card, and source card."""
    repo.create_user(email="test@example.com", display_name="Test User")

    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en="Black Lotus",
            set_code="lea",
            collector_number="232",
        )
        session.add(card)
        session.commit()
        session.refresh(card)
        card_id = card.id

        source = SourceCardRow(
            source="liga",
            external_id=f"liga_{card_id}",
            card_id=card_id,
            url=f"https://example.com/{card_id}",
        )
        session.add(source)

        # Add a price observation
        obs = PriceObservationRow(
            source="liga",
            external_id=f"liga_{card_id}",
            observed_at=date.today(),
            median_price=Decimal("100.00"),
            currency="BRL",
        )
        session.add(obs)
        session.commit()

    return {"user_id": 1, "card_id": card_id}


class TestCheckAlertsForCard:
    def test_no_alerts(self, repo, setup_data):
        """No alerts exist, nothing triggered."""
        with Session(repo.engine) as session:
            triggered = check_alerts_for_card(setup_data["card_id"], Decimal("50.00"), session)
            assert triggered == 0

    def test_below_alert_triggers(self, repo, setup_data):
        """Alert with direction=below triggers when price drops."""
        with Session(repo.engine) as session:
            alert = PriceAlertRow(
                user_id=setup_data["user_id"],
                card_id=setup_data["card_id"],
                target_price=Decimal("80.00"),
                direction="below",
                is_active=1,
            )
            session.add(alert)
            session.commit()

            triggered = check_alerts_for_card(setup_data["card_id"], Decimal("75.00"), session)
            assert triggered == 1

            # Verify alert is now inactive
            session.refresh(alert)
            assert alert.is_active == 0
            assert alert.triggered_at is not None

            # Verify notification was created
            notifications = session.query(AlertNotificationRow).all()
            assert len(notifications) == 1
            assert notifications[0].card_name == "Black Lotus"
            assert notifications[0].new_price == Decimal("75.00")

    def test_below_alert_exact_match(self, repo, setup_data):
        """Alert triggers when price equals target."""
        with Session(repo.engine) as session:
            alert = PriceAlertRow(
                user_id=setup_data["user_id"],
                card_id=setup_data["card_id"],
                target_price=Decimal("50.00"),
                direction="below",
                is_active=1,
            )
            session.add(alert)
            session.commit()

            triggered = check_alerts_for_card(setup_data["card_id"], Decimal("50.00"), session)
            assert triggered == 1

    def test_below_alert_not_triggered(self, repo, setup_data):
        """Alert with direction=below does NOT trigger when price is above target."""
        with Session(repo.engine) as session:
            alert = PriceAlertRow(
                user_id=setup_data["user_id"],
                card_id=setup_data["card_id"],
                target_price=Decimal("80.00"),
                direction="below",
                is_active=1,
            )
            session.add(alert)
            session.commit()

            triggered = check_alerts_for_card(setup_data["card_id"], Decimal("90.00"), session)
            assert triggered == 0
            session.refresh(alert)
            assert alert.is_active == 1

    def test_above_alert_triggers(self, repo, setup_data):
        """Alert with direction=above triggers when price rises."""
        with Session(repo.engine) as session:
            alert = PriceAlertRow(
                user_id=setup_data["user_id"],
                card_id=setup_data["card_id"],
                target_price=Decimal("120.00"),
                direction="above",
                is_active=1,
            )
            session.add(alert)
            session.commit()

            triggered = check_alerts_for_card(setup_data["card_id"], Decimal("150.00"), session)
            assert triggered == 1

    def test_above_alert_not_triggered(self, repo, setup_data):
        """Alert with direction=above does NOT trigger when price is below target."""
        with Session(repo.engine) as session:
            alert = PriceAlertRow(
                user_id=setup_data["user_id"],
                card_id=setup_data["card_id"],
                target_price=Decimal("120.00"),
                direction="above",
                is_active=1,
            )
            session.add(alert)
            session.commit()

            triggered = check_alerts_for_card(setup_data["card_id"], Decimal("110.00"), session)
            assert triggered == 0

    def test_inactive_alert_ignored(self, repo, setup_data):
        """Inactive alerts are not checked."""
        with Session(repo.engine) as session:
            alert = PriceAlertRow(
                user_id=setup_data["user_id"],
                card_id=setup_data["card_id"],
                target_price=Decimal("200.00"),
                direction="below",
                is_active=0,
                triggered_at=datetime.now(),
            )
            session.add(alert)
            session.commit()

            triggered = check_alerts_for_card(setup_data["card_id"], Decimal("50.00"), session)
            assert triggered == 0

    def test_multiple_alerts_triggered(self, repo, setup_data):
        """Multiple alerts for the same card can trigger at once."""
        with Session(repo.engine) as session:
            a1 = PriceAlertRow(
                user_id=setup_data["user_id"],
                card_id=setup_data["card_id"],
                target_price=Decimal("80.00"),
                direction="below",
                is_active=1,
            )
            a2 = PriceAlertRow(
                user_id=setup_data["user_id"],
                card_id=setup_data["card_id"],
                target_price=Decimal("90.00"),
                direction="below",
                is_active=1,
            )
            session.add_all([a1, a2])
            session.commit()

            triggered = check_alerts_for_card(setup_data["card_id"], Decimal("70.00"), session)
            assert triggered == 2


class TestCheckAlertsAfterScan:
    def test_scan_triggers_alerts(self, repo, setup_data):
        """Scan completion triggers alerts for updated cards."""
        card_id = setup_data["card_id"]

        with Session(repo.engine) as session:
            alert = PriceAlertRow(
                user_id=setup_data["user_id"],
                card_id=card_id,
                target_price=Decimal("80.00"),
                direction="above",
                is_active=1,
            )
            session.add(alert)
            session.commit()

        scan_run = ScanRun(
            id=1,
            scan_type="liga_full",
            status="completed",
            cards_total=1,
            cards_processed=1,
        )

        triggered = check_alerts_after_scan(scan_run, [f"liga_{card_id}"], repo)
        assert triggered == 1

    def test_scan_no_external_ids(self, repo, setup_data):
        """Empty external_ids list does nothing."""
        scan_run = ScanRun(
            id=1,
            scan_type="liga_full",
            status="completed",
            cards_total=0,
            cards_processed=0,
        )

        triggered = check_alerts_after_scan(scan_run, [], repo)
        assert triggered == 0

    def test_scan_unknown_external_id(self, repo, setup_data):
        """Unknown external_ids are silently skipped."""
        scan_run = ScanRun(
            id=1,
            scan_type="liga_full",
            status="completed",
            cards_total=1,
            cards_processed=1,
        )

        triggered = check_alerts_after_scan(scan_run, ["liga_99999"], repo)
        assert triggered == 0


class TestMakeAlertCheckerHook:
    def test_hook_callable(self, repo, setup_data):
        """Hook returned by make_alert_checker_hook is callable."""
        hook = make_alert_checker_hook(repo)
        assert callable(hook)

        scan_run = ScanRun(
            id=1,
            scan_type="liga_full",
            status="completed",
            cards_total=0,
            cards_processed=0,
        )
        # Should not raise
        hook(scan_run, [])

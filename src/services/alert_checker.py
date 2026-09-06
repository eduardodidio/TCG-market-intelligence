"""Alert checker service — checks price alerts after price updates (F106-T02).

Called from scan hooks after a scan completes. Resolves external_ids to card_ids
and checks all active alerts for those cards.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import structlog
from sqlalchemy import select
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

log = structlog.get_logger()


def check_alerts_for_card(
    card_id: int,
    new_price: Decimal,
    session: Session,
) -> int:
    """Check and trigger active alerts for a single card.

    Args:
        card_id: The card whose price was updated.
        new_price: The new price observed.
        session: Active SQLAlchemy session.

    Returns:
        Number of alerts triggered.
    """
    alerts = session.scalars(
        select(PriceAlertRow).where(
            PriceAlertRow.card_id == card_id,
            PriceAlertRow.is_active == 1,
        )
    ).all()

    if not alerts:
        return 0

    # Get card name for notification
    card = session.get(CardRow, card_id)
    card_name = card.name_en if card else f"Card #{card_id}"

    # Get old price (previous observation for this card)
    old_price = _get_previous_price(card_id, session)

    triggered = 0
    now = datetime.now()

    for alert in alerts:
        target = Decimal(str(alert.target_price))
        should_trigger = False

        if alert.direction == "below" and new_price <= target:
            should_trigger = True
        elif alert.direction == "above" and new_price >= target:
            should_trigger = True

        if should_trigger:
            alert.is_active = 0
            alert.triggered_at = now

            notification = AlertNotificationRow(
                alert_id=alert.id,
                card_name=card_name,
                old_price=old_price,
                new_price=new_price,
                is_read=0,
                notified_at=now,
            )
            session.add(notification)
            triggered += 1

            log.info(
                "alert_triggered",
                alert_id=alert.id,
                card_id=card_id,
                card_name=card_name,
                direction=alert.direction,
                target_price=str(target),
                new_price=str(new_price),
            )

    if triggered > 0:
        session.commit()

    return triggered


def _get_previous_price(card_id: int, session: Session) -> Decimal | None:
    """Get the most recent price observation for a card (before today)."""
    # Find source cards linked to this card_id
    external_ids = session.scalars(
        select(SourceCardRow.external_id).where(
            SourceCardRow.card_id == card_id,
            SourceCardRow.external_id.isnot(None),
        )
    ).all()

    if not external_ids:
        return None

    # Get the latest observation across all source cards
    row = session.execute(
        select(PriceObservationRow.median_price)
        .where(PriceObservationRow.external_id.in_(external_ids))
        .order_by(PriceObservationRow.observed_at.desc())
        .limit(1)
    ).first()

    if row and row[0] is not None:
        return Decimal(str(row[0]))
    return None


def check_alerts_after_scan(
    scan_run: ScanRun,
    external_ids: list[str],
    repo: Repository,
) -> int:
    """Check alerts for all cards updated in a scan.

    This is designed to be called from a scan hook.

    Args:
        scan_run: The completed scan run.
        external_ids: List of external_ids that were updated.
        repo: Repository instance.

    Returns:
        Total number of alerts triggered.
    """
    if not external_ids:
        return 0

    total_triggered = 0

    with Session(repo.engine) as session:
        # Resolve external_ids -> (card_id, latest_price) pairs
        for ext_id in external_ids:
            # Find the card_id for this external_id
            source_card = session.execute(
                select(SourceCardRow.card_id).where(
                    SourceCardRow.external_id == ext_id,
                    SourceCardRow.card_id.isnot(None),
                )
            ).first()

            if source_card is None:
                continue

            card_id = source_card[0]

            # Get latest price for this external_id
            price_row = session.execute(
                select(PriceObservationRow.median_price)
                .where(PriceObservationRow.external_id == ext_id)
                .order_by(PriceObservationRow.observed_at.desc())
                .limit(1)
            ).first()

            if price_row is None or price_row[0] is None:
                continue

            new_price = Decimal(str(price_row[0]))
            triggered = check_alerts_for_card(card_id, new_price, session)
            total_triggered += triggered

    if total_triggered > 0:
        log.info(
            "alerts_checked_after_scan",
            scan_id=scan_run.id,
            external_ids_count=len(external_ids),
            alerts_triggered=total_triggered,
        )

    return total_triggered


def make_alert_checker_hook(repo: Repository):
    """Create a scan hook that checks price alerts after a scan completes.

    Usage:
        from src.services.alert_checker import make_alert_checker_hook
        hook = make_alert_checker_hook(repo)
        default_registry.register(hook)
    """

    def _hook(scan_run: ScanRun, external_ids: list[str]) -> None:
        check_alerts_after_scan(scan_run, external_ids, repo)

    return _hook

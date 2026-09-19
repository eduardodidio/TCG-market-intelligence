"""Price alerts API router (F106-T01)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.api.error_codes import ErrorCode, api_error
from src.api.schemas.envelope import ApiResponse, success_response
from src.database.models import AlertNotificationRow, CardRow, PriceAlertRow, PriceObservationRow
from src.database.repository import Repository
from src.domain.models import User

log = structlog.get_logger()

router = APIRouter(prefix="/alerts", tags=["alerts"])

MAX_ACTIVE_ALERTS_PER_USER = 50


# --- Schemas ---


class CreateAlertRequest(BaseModel):
    card_id: int
    target_price: float = Field(..., gt=0)
    direction: str = Field(..., pattern="^(below|above)$")


class UpdateAlertRequest(BaseModel):
    target_price: float | None = Field(None, gt=0)
    direction: str | None = Field(None, pattern="^(below|above)$")


class AlertResponse(BaseModel):
    id: int
    card_id: int
    card_name: str | None = None
    target_price: float
    direction: str
    is_active: bool
    triggered_at: str | None = None
    created_at: str
    current_price: float | None = None


class AlertNotificationResponse(BaseModel):
    id: int
    alert_id: int
    card_id: int
    card_name: str
    old_price: float | None = None
    new_price: float
    is_read: bool
    notified_at: str


class NotificationsListResponse(BaseModel):
    notifications: list[AlertNotificationResponse]
    unread_count: int


# --- Endpoints ---


@router.post("", response_model=ApiResponse[AlertResponse])
def create_alert(
    request: CreateAlertRequest,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Create a new price alert for a card."""
    with Session(repo.engine) as session:
        # Check card exists
        card = session.get(CardRow, request.card_id)
        if card is None:
            raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Card not found")

        # Check max active alerts
        active_count = session.scalar(
            select(func.count(PriceAlertRow.id)).where(
                PriceAlertRow.user_id == user.id,
                PriceAlertRow.is_active == 1,
            )
        )
        if active_count >= MAX_ACTIVE_ALERTS_PER_USER:
            raise api_error(
                409,
                ErrorCode.VALIDATION_LIMIT_EXCEEDED,
                f"Maximum {MAX_ACTIVE_ALERTS_PER_USER} active alerts allowed",
            )

        alert = PriceAlertRow(
            user_id=user.id,
            card_id=request.card_id,
            target_price=Decimal(str(request.target_price)),
            direction=request.direction,
            is_active=1,
            created_at=datetime.now(),
        )
        session.add(alert)
        session.commit()
        session.refresh(alert)

        return success_response(
            AlertResponse(
                id=alert.id,
                card_id=alert.card_id,
                card_name=card.name_en,
                target_price=float(alert.target_price),
                direction=alert.direction,
                is_active=bool(alert.is_active),
                triggered_at=alert.triggered_at.isoformat() if alert.triggered_at else None,
                created_at=alert.created_at.isoformat(),
            )
        )


@router.get("", response_model=ApiResponse[list[AlertResponse]])
def list_alerts(
    status: str = Query("all", pattern="^(active|triggered|all)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """List the current user's price alerts."""
    with Session(repo.engine) as session:
        query = (
            select(PriceAlertRow, CardRow.name_en)
            .outerjoin(CardRow, PriceAlertRow.card_id == CardRow.id)
            .where(PriceAlertRow.user_id == user.id)
        )

        if status == "active":
            query = query.where(PriceAlertRow.is_active == 1)
        elif status == "triggered":
            query = query.where(PriceAlertRow.is_active == 0)

        total = session.scalar(select(func.count()).select_from(query.subquery()))

        query = query.order_by(PriceAlertRow.created_at.desc()).offset(offset).limit(limit)
        rows = session.execute(query).all()

        # Fetch latest prices for all alert card_ids
        card_ids = list({alert.card_id for alert, _ in rows})
        latest_prices: dict[int, float] = {}
        for cid in card_ids:
            ext_id = f"liga_{cid}"
            price_row = session.execute(
                select(PriceObservationRow.median_price)
                .where(PriceObservationRow.external_id == ext_id)
                .order_by(PriceObservationRow.observed_at.desc())
                .limit(1)
            ).first()
            if price_row and price_row[0] is not None:
                latest_prices[cid] = float(price_row[0])

        alerts = [
            AlertResponse(
                id=alert.id,
                card_id=alert.card_id,
                card_name=card_name,
                target_price=float(alert.target_price),
                direction=alert.direction,
                is_active=bool(alert.is_active),
                triggered_at=alert.triggered_at.isoformat() if alert.triggered_at else None,
                created_at=alert.created_at.isoformat(),
                current_price=latest_prices.get(alert.card_id),
            )
            for alert, card_name in rows
        ]

        return success_response(alerts, total=total)


@router.get("/notifications", response_model=ApiResponse[NotificationsListResponse])
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """List alert notifications for the current user."""
    with Session(repo.engine) as session:
        query = (
            select(AlertNotificationRow, PriceAlertRow.card_id)
            .join(PriceAlertRow, AlertNotificationRow.alert_id == PriceAlertRow.id)
            .where(PriceAlertRow.user_id == user.id)
        )

        if unread_only:
            query = query.where(AlertNotificationRow.is_read == 0)

        query = query.order_by(AlertNotificationRow.notified_at.desc()).limit(limit)
        rows = session.execute(query).all()

        # Unread count (always full, not filtered by limit)
        unread_count = (
            session.scalar(
                select(func.count(AlertNotificationRow.id))
                .join(PriceAlertRow, AlertNotificationRow.alert_id == PriceAlertRow.id)
                .where(
                    PriceAlertRow.user_id == user.id,
                    AlertNotificationRow.is_read == 0,
                )
            )
            or 0
        )

        notifications = [
            AlertNotificationResponse(
                id=n.id,
                alert_id=n.alert_id,
                card_id=card_id,
                card_name=n.card_name,
                old_price=float(n.old_price) if n.old_price is not None else None,
                new_price=float(n.new_price),
                is_read=bool(n.is_read),
                notified_at=n.notified_at.isoformat(),
            )
            for n, card_id in rows
        ]

        return success_response(
            NotificationsListResponse(
                notifications=notifications,
                unread_count=unread_count,
            )
        )


@router.patch("/{alert_id}", response_model=ApiResponse[AlertResponse])
def update_alert(
    alert_id: int,
    request: UpdateAlertRequest,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Update a price alert (only owner can update, only active alerts)."""
    with Session(repo.engine) as session:
        alert = session.get(PriceAlertRow, alert_id)
        if alert is None:
            raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Alert not found")
        if alert.user_id != user.id:
            raise api_error(403, ErrorCode.AUTHZ_FORBIDDEN, "Not authorized to update this alert")
        if not alert.is_active:
            raise api_error(
                409, ErrorCode.VALIDATION_LIMIT_EXCEEDED, "Cannot edit a triggered alert"
            )

        # Apply partial updates
        if request.target_price is not None:
            alert.target_price = Decimal(str(request.target_price))
        if request.direction is not None:
            alert.direction = request.direction

        session.commit()
        session.refresh(alert)

        # Get card name
        card = session.get(CardRow, alert.card_id)
        card_name = card.name_en if card else None

        return success_response(
            AlertResponse(
                id=alert.id,
                card_id=alert.card_id,
                card_name=card_name,
                target_price=float(alert.target_price),
                direction=alert.direction,
                is_active=bool(alert.is_active),
                triggered_at=alert.triggered_at.isoformat() if alert.triggered_at else None,
                created_at=alert.created_at.isoformat(),
            )
        )


@router.delete("/{alert_id}", status_code=204)
def delete_alert(
    alert_id: int,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Delete a price alert (only owner can delete)."""
    with Session(repo.engine) as session:
        alert = session.get(PriceAlertRow, alert_id)
        if alert is None:
            raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Alert not found")
        if alert.user_id != user.id:
            raise api_error(403, ErrorCode.AUTHZ_FORBIDDEN, "Not authorized to delete this alert")

        session.delete(alert)
        session.commit()


@router.patch("/notifications/read", response_model=ApiResponse[dict])
def mark_all_read(
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    with Session(repo.engine) as session:
        # Get all alert IDs for this user
        alert_ids = session.scalars(
            select(PriceAlertRow.id).where(PriceAlertRow.user_id == user.id)
        ).all()

        if alert_ids:
            from sqlalchemy import update

            session.execute(
                update(AlertNotificationRow)
                .where(
                    AlertNotificationRow.alert_id.in_(alert_ids),
                    AlertNotificationRow.is_read == 0,
                )
                .values(is_read=1)
            )
            session.commit()

        return success_response({"marked_read": True})

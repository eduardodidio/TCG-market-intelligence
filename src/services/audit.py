"""Audit logging service for admin actions (F100)."""

from __future__ import annotations

from src.database.repository import Repository
from src.domain.models import User


class AuditService:
    """Fire-and-forget audit logger for admin actions.

    Wraps repository calls and silently swallows exceptions
    so audit failures never block the admin action itself.
    """

    def __init__(self, repo: Repository):
        self._repo = repo

    def log(
        self,
        actor: User,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Log an admin action. Fire-and-forget -- never raises."""
        try:
            self._repo.log_audit(
                actor_id=actor.id,
                actor_email=actor.email,
                action=action,
                target_type=target_type,
                target_id=str(target_id) if target_id is not None else None,
                details=details,
                ip_address=ip_address,
            )
        except Exception:
            import structlog

            structlog.get_logger().warning("audit_log_failed", action=action)

"""News feed API router (F166)."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.api.deps import get_current_user, get_db
from src.api.schemas.envelope import ApiResponse, success_response
from src.database.repository import Repository
from src.domain.models import User

log = structlog.get_logger()

router = APIRouter(prefix="/news", tags=["news"])


# --- Schemas ---


class NewsItemResponse(BaseModel):
    id: int
    title: str
    summary: str | None = None
    source_url: str
    source_name: str
    category: str
    image_url: str | None = None
    published_at: str | None = None
    fetched_at: str | None = None
    is_read: bool


class NewsListResponse(BaseModel):
    items: list[NewsItemResponse]
    total: int


class UnreadCountResponse(BaseModel):
    count: int


class NewsStatusResponse(BaseModel):
    total_items: int
    last_fetched_at: str | None = None
    newest_published_at: str | None = None


# --- Endpoints ---


@router.get("", response_model=ApiResponse[NewsListResponse])
def list_news(
    filter: str = Query("all", pattern="^(all|unread|read)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: str | None = Query(None),
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """List news items with read status for the current user."""
    items = repo.list_news_items(
        user_id=user.id,
        filter=filter,
        limit=limit,
        offset=offset,
        category=category,
    )
    total = repo.count_news_items(
        user_id=user.id,
        filter=filter,
        category=category,
    )

    news_items = [NewsItemResponse(**item) for item in items]
    return success_response(NewsListResponse(items=news_items, total=total))


@router.post("/{news_id}/mark-read", response_model=ApiResponse[dict])
def mark_news_read(
    news_id: int,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Mark a news item as read (idempotent)."""
    repo.mark_news_read(user_id=user.id, news_item_id=news_id)
    return success_response({"marked": True})


@router.post("/{news_id}/mark-unread", response_model=ApiResponse[dict])
def mark_news_unread(
    news_id: int,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Mark a news item as unread (idempotent)."""
    repo.mark_news_unread(user_id=user.id, news_item_id=news_id)
    return success_response({"marked": True})


@router.get("/unread-count", response_model=ApiResponse[UnreadCountResponse])
def get_unread_count(
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Get the count of unread news items for the current user."""
    count = repo.count_unread_news(user_id=user.id)
    return success_response(UnreadCountResponse(count=count))


@router.get("/status", response_model=ApiResponse[NewsStatusResponse])
def get_news_status(
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Get aggregate freshness info for the news feed (read-only, no network I/O)."""
    status = repo.get_news_status()
    return success_response(NewsStatusResponse(**status))

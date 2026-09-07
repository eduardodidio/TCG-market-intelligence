"""Achievements API router (F109)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.deps import get_current_user, get_db
from src.api.schemas.envelope import success_response
from src.database.repository import Repository
from src.domain.models import User
from src.services.achievements import (
    check_achievements,
    get_user_achievements,
)

router = APIRouter(prefix="/achievements", tags=["achievements"])


@router.get("")
def list_achievements(
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """List all achievements with unlocked status for current user.

    Title and description are returned in both languages;
    the frontend selects the correct language based on user preference.
    """
    achievements = get_user_achievements(user.id, repo)

    # Select title/description based on user's preferred language
    lang_suffix = "_pt" if user.preferred_language == "pt-BR" else "_en"
    result = []
    for a in achievements:
        result.append(
            {
                "key": a["key"],
                "title": a[f"title{lang_suffix}"],
                "description": a[f"description{lang_suffix}"],
                "icon": a["icon"],
                "unlocked": a["unlocked"],
                "unlocked_at": a["unlocked_at"],
            }
        )

    return success_response(data=result)


@router.post("/check")
def trigger_check(
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Trigger achievement check for current user.

    Returns list of newly unlocked achievement keys.
    """
    newly_unlocked = check_achievements(user.id, repo)
    return success_response(data={"newly_unlocked": newly_unlocked})

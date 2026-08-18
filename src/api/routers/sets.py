from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.deps import get_db
from src.api.schemas.envelope import ApiResponse, success_response
from src.api.schemas.sets import SetSummary
from src.database.repository import Repository

router = APIRouter(prefix="/sets", tags=["sets"])


@router.get("", response_model=ApiResponse[list[SetSummary]])
def list_sets(
    game: str | None = None,
    repo: Repository = Depends(get_db),
):
    results = repo.list_sets(game=game)
    data = [SetSummary(game=r[0], set_code=r[1], card_count=r[2]) for r in results]
    return success_response(data=data)

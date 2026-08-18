from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class Meta(BaseModel):
    cursor: str | None = None
    total: int | None = None
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ApiResponse(BaseModel, Generic[T]):
    data: T | None = None
    meta: Meta = Field(default_factory=Meta)
    errors: list[ErrorDetail] = Field(default_factory=list)


def success_response(data: T, meta: Meta | None = None, **meta_kwargs: object) -> ApiResponse[T]:
    if meta is None:
        meta = Meta(**meta_kwargs)
    return ApiResponse(data=data, meta=meta)


def error_response(errors: list[ErrorDetail], **meta_kwargs: object) -> ApiResponse:
    return ApiResponse(data=None, meta=Meta(**meta_kwargs), errors=errors)


def paginated_response(
    data: T,
    cursor: str | None,
    total: int | None = None,
    **meta_kwargs: object,
) -> ApiResponse[T]:
    meta = Meta(cursor=cursor, total=total, **meta_kwargs)
    return ApiResponse(data=data, meta=meta)

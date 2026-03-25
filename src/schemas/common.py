"""Common schema mixins and base models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime | None = None


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=1000)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class APIResponse[T](BaseSchema):
    success: bool = True
    data: T | None = None
    message: str | None = None
    errors: list[dict[str, Any]] | None = None


class PaginatedResponse[T](BaseSchema):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

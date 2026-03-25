"""Workspace schemas."""

import uuid

from pydantic import BaseModel, Field

from src.schemas.common import BaseSchema, TimestampMixin


class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None


class WorkspaceResponse(BaseSchema, TimestampMixin):
    id: uuid.UUID
    name: str
    slug: str
    is_active: bool

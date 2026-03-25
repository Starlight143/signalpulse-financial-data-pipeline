"""Database-agnostic types that work across PostgreSQL and SQLite."""

import uuid
from typing import Any

from sqlalchemy import JSON, String, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class GUID(TypeDecorator[uuid.UUID]):
    """Platform-independent GUID type that stores UUID as String in SQLite and UUID in PostgreSQL."""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return PG_UUID(as_uuid=True)
        return String(36)

    def process_bind_param(self, value: uuid.UUID | None, dialect: Any) -> str | None:
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        return str(value)

    def process_result_value(
        self, value: str | uuid.UUID | None, _dialect: Any
    ) -> uuid.UUID | None:
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class JSONDict(TypeDecorator[dict[str, Any]]):
    """Platform-independent JSON type that uses JSONB in PostgreSQL and JSON in SQLite."""

    impl = JSON()
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return JSONB()
        return JSON()

    def process_bind_param(
        self, value: dict[str, Any] | None, _dialect: Any
    ) -> dict[str, Any] | None:
        return value

    def process_result_value(
        self, value: dict[str, Any] | None, _dialect: Any
    ) -> dict[str, Any] | None:
        return value


class JSONList(TypeDecorator[list[Any]]):
    """Platform-independent JSON list type that uses JSONB in PostgreSQL and JSON in SQLite."""

    impl = JSON()
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return JSONB()
        return JSON()

    def process_bind_param(self, value: list[Any] | None, _dialect: Any) -> list[Any] | None:
        return value

    def process_result_value(self, value: list[Any] | None, _dialect: Any) -> list[Any] | None:
        if value is None:
            return []
        return value

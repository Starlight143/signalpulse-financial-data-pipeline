"""Dependency injection for FastAPI."""

import httpx
from fastapi import Request

from src.database import get_session


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Return the shared httpx.AsyncClient stored in app.state during lifespan."""
    return request.app.state.http_client


__all__ = ["get_session", "get_http_client"]

"""Stage0 integration module."""

from src.stage0.adapter import Stage0Adapter, get_stage0_adapter
from src.stage0.client import Stage0Client
from src.stage0.context import build_context
from src.stage0.exceptions import (
    Stage0AuthorizationError,
    Stage0ConnectionError,
    Stage0DeferredError,
    Stage0Error,
    Stage0TimeoutError,
)
from src.stage0.live_adapter import LiveStage0Adapter
from src.stage0.mock_adapter import MockStage0Adapter

__all__ = [
    "Stage0Client",
    "Stage0Adapter",
    "LiveStage0Adapter",
    "MockStage0Adapter",
    "get_stage0_adapter",
    "build_context",
    "Stage0Error",
    "Stage0AuthorizationError",
    "Stage0ConnectionError",
    "Stage0TimeoutError",
    "Stage0DeferredError",
]

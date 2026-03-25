"""Stage0 adapter interface."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from src.config import get_settings
from src.schemas.stage0 import Stage0Request, Stage0Response

if TYPE_CHECKING:
    import httpx

    from src.stage0.client import Stage0Client  # noqa: F401
    from src.stage0.live_adapter import LiveStage0Adapter  # noqa: F401
    from src.stage0.mock_adapter import MockStage0Adapter  # noqa: F401

settings = get_settings()


class Stage0Adapter(ABC):
    @abstractmethod
    async def check(self, request: Stage0Request) -> Stage0Response:
        pass

    @abstractmethod
    def is_mock(self) -> bool:
        pass


def get_stage0_adapter(
    mock_mode: bool | None = None,
    client: "Stage0Client | None" = None,
    http_client: "httpx.AsyncClient | None" = None,
) -> "Stage0Adapter":
    from src.stage0.client import Stage0Client
    from src.stage0.live_adapter import LiveStage0Adapter
    from src.stage0.mock_adapter import MockStage0Adapter

    use_mock = mock_mode if mock_mode is not None else settings.is_stage0_mock_mode

    if use_mock:
        return MockStage0Adapter()

    actual_client = client or Stage0Client(http_client=http_client)
    return LiveStage0Adapter(client=actual_client)

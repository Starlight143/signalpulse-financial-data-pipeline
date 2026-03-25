"""Live Stage0 adapter for production use."""

from src.schemas.stage0 import Stage0Request, Stage0Response
from src.stage0.adapter import Stage0Adapter
from src.stage0.client import Stage0Client
from src.stage0.exceptions import (
    Stage0AuthorizationError,
    Stage0DeferredError,
)


class LiveStage0Adapter(Stage0Adapter):
    def __init__(self, client: Stage0Client | None = None):
        self.client = client or Stage0Client()

    async def check(self, request: Stage0Request) -> Stage0Response:
        response = await self.client.check(request)

        if response.verdict == "ALLOW":
            return response

        if response.verdict == "DENY":
            raise Stage0AuthorizationError(
                verdict="DENY",
                issues=[i.model_dump() for i in response.issues],
                request_id=response.request_id,
            )

        if response.verdict == "DEFER":
            raise Stage0DeferredError(
                issues=[i.model_dump() for i in response.issues],
                clarifying_questions=response.clarifying_questions,
                request_id=response.request_id,
            )

        raise Stage0AuthorizationError(
            verdict="UNKNOWN",
            issues=[
                {"code": "UNKNOWN_VERDICT", "message": f"Unexpected verdict: {response.verdict}"}
            ],
            request_id=response.request_id,
        )

    def is_mock(self) -> bool:
        return False

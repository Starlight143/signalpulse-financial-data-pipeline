"""Workspace context middleware."""

import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


class WorkspaceMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        default_workspace_id: str = "00000000-0000-0000-0000-000000000001",
    ) -> None:
        super().__init__(app)
        self.default_workspace_id = uuid.UUID(default_workspace_id)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        workspace_header = request.headers.get("X-Workspace-ID")

        if workspace_header:
            try:
                workspace_id = uuid.UUID(workspace_header)
            except ValueError:
                workspace_id = self.default_workspace_id
        else:
            workspace_id = self.default_workspace_id

        request.state.workspace_id = workspace_id

        response = await call_next(request)
        return response

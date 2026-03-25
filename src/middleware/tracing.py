"""Request tracing middleware."""

import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = structlog.get_logger()


class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        span_id = str(uuid.uuid4())[:16]

        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            span_id=span_id,
        )

        request.state.trace_id = trace_id
        request.state.span_id = span_id

        try:
            response = await call_next(request)
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Span-ID"] = span_id
            return response
        finally:
            structlog.contextvars.unbind_contextvars("trace_id", "span_id")

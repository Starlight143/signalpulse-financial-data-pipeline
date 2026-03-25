"""Application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import api_router
from src.config import get_settings
from src.database import close_db, init_db
from src.middleware.logging import LoggingMiddleware
from src.middleware.tracing import TracingMiddleware

settings = get_settings()


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(message)s",
    )

    if settings.structured_logging:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                logging.getLevelName(settings.log_level)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    logger = structlog.get_logger()
    logger.info("application_starting", app=settings.app_name, env=settings.app_env)

    # Shared HTTP client: reuses TCP connections for Stage0 and webhook calls.
    http_client = httpx.AsyncClient(timeout=float(settings.stage0_timeout_seconds))
    app.state.http_client = http_client
    logger.info("http_client_initialized")

    await init_db()
    logger.info("database_initialized")

    yield

    await http_client.aclose()
    logger.info("http_client_closed")
    await close_db()
    logger.info("application_shutdown")


app = FastAPI(
    title="SignalPulse Financial Data Pipeline",
    description=(
        "Production-ready financial data pipeline with SignalPulse Stage0 "
        "runtime authorization for multi-source market data ingestion, "
        "feature engineering, and risk-gated action execution."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.request_tracing:
    app.add_middleware(TracingMiddleware)

if settings.structured_logging:
    app.add_middleware(LoggingMiddleware)

app.include_router(api_router)


def main() -> None:
    import uvicorn

    # uvicorn does not allow reload=True with workers>1; use a single worker in debug mode.
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=1 if settings.debug else settings.api_workers,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()

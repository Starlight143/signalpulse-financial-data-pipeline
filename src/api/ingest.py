"""Ingestion trigger API endpoints."""

import hmac
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status

from src.config import get_settings
from src.ingestion.worker import IngestionWorker
from src.schemas.common import APIResponse

router = APIRouter()
settings = get_settings()
logger = structlog.get_logger()


def _get_default_workspace_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


async def verify_internal_api_key(
    x_internal_key: str | None = Header(None, alias="X-Internal-Key"),
) -> bool:
    if not x_internal_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing internal API key",
        )
    # Constant-time comparison prevents timing-based key enumeration.
    if not hmac.compare_digest(x_internal_key, settings.internal_api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing internal API key",
        )
    return True


@router.post("/run", response_model=APIResponse[dict[str, Any]])
async def trigger_ingestion(
    workspace_id: uuid.UUID = Depends(_get_default_workspace_id),
    _: bool = Depends(verify_internal_api_key),
) -> APIResponse[dict[str, Any]]:
    try:
        worker = IngestionWorker()
        results = await worker.run_once(workspace_id)

        successful = sum(1 for r in results.values() if r.success)
        total = len(results)

        logger.info(
            "ingestion_triggered",
            workspace_id=str(workspace_id),
            successful=successful,
            total=total,
        )

        return APIResponse(
            success=True,
            data={
                "successful_jobs": successful,
                "total_jobs": total,
                "results": {
                    k: {
                        "success": v.success,
                        "records_fetched": v.records_fetched,
                        "records_stored": v.records_stored,
                        "error": v.error_message,
                    }
                    for k, v in results.items()
                },
            },
            message=f"Ingestion completed: {successful}/{total} jobs successful",
        )

    except Exception as e:
        logger.error("ingestion_trigger_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ingestion trigger failed",
        )

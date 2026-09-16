import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.models import LivenessResponse, ReadinessResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LivenessResponse)
async def live() -> LivenessResponse:
    return LivenessResponse(status="ok", service="giftfind-api")


@router.get("/health/ready", response_model=ReadinessResponse)
async def ready(request: Request) -> ReadinessResponse | JSONResponse:
    try:
        connected = await request.app.state.redis.ping()
    except Exception:
        logger.warning("Redis readiness probe failed", exc_info=True)
        connected = False

    if not connected:
        response = ReadinessResponse(
            status="unavailable",
            redis="unavailable",
            environment=request.app.state.settings.app_env,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=response.model_dump()
        )

    return ReadinessResponse(
        status="ready",
        redis="connected",
        environment=request.app.state.settings.app_env,
    )

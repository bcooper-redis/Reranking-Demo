from fastapi import APIRouter, Query, Request

from app.api.context import catalog, telemetry
from app.models import (
    AutocompleteResponse,
    ComparisonResponse,
    PublicConfigResponse,
    SearchRequest,
    SearchResponse,
)

router = APIRouter()


@router.get("/api/v1/config/public", response_model=PublicConfigResponse, tags=["configuration"])
async def public_config(request: Request) -> PublicConfigResponse:
    return await catalog(request).public_config(request.app.state.retailers.values())


@router.get(
    "/api/v1/search/suggestions",
    response_model=AutocompleteResponse,
    tags=["search"],
)
async def autocomplete(
    request: Request,
    q: str = Query(min_length=1, max_length=300),
    tenant_id: str = Query(default="general", min_length=1, max_length=80),
    limit: int = Query(default=5, ge=1, le=8),
) -> AutocompleteResponse:
    return await catalog(request).autocomplete(q, tenant_id, limit)


@router.post("/api/v1/search", response_model=SearchResponse | ComparisonResponse, tags=["search"])
async def search(request: Request, payload: SearchRequest) -> SearchResponse | ComparisonResponse:
    response = await catalog(request).search(payload)
    await telemetry(request).record_impression(
        response,
        tenant_id=payload.tenant_id,
        profile_id=payload.profile_id,
    )
    return response

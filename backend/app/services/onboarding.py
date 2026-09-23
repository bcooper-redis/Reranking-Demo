from fastapi import HTTPException, Request, status

from app.evaluation import EvaluationService
from app.models.onboarding import (
    RetailerDeleteResponse,
    RetailerImportRequest,
    RetailerImportResponse,
)
from app.retailers import RETAILERS
from app.retailers.onboarding import (
    build_retailer,
    is_builtin,
    retailer_id_for,
    save_payload,
)
from app.retrieval import CatalogService
from app.telemetry import TelemetryService


async def import_retailer(
    request: Request, payload: RetailerImportRequest
) -> RetailerImportResponse:
    retailer_id = retailer_id_for(payload.organization_name)
    if is_builtin(retailer_id, RETAILERS):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Built-in retailer identities cannot be replaced from the demo foundry",
        )

    retailer = build_retailer(payload)
    existing = request.app.state.catalogs.get(retailer_id)
    if existing is not None:
        await existing.reset()
        await existing.close()

    catalog = CatalogService(request.app.state.settings, request.app.state.redis.client, retailer)
    catalog_count = await catalog.seed(
        retailer.generate_catalog(len(payload.products)),
        retailer.tenants(),
        retailer.profiles(),
        retailer.promotions(),
    )
    request.app.state.retailers[retailer_id] = retailer
    request.app.state.catalogs[retailer_id] = catalog
    request.app.state.evaluations[retailer_id] = EvaluationService(
        request.app.state.settings, request.app.state.redis.client, catalog
    )
    request.app.state.telemetries[retailer_id] = TelemetryService(
        request.app.state.redis.client, retailer.redis
    )
    await save_payload(request.app.state.redis.client, payload)
    return RetailerImportResponse(
        retailer_id=retailer_id,
        organization_name=retailer.organization_name,
        experience_name=retailer.experience_name,
        catalog_count=catalog_count,
        index_alias=retailer.redis.catalog_index_alias,
    )


async def delete_retailer(request: Request, retailer_id: str) -> RetailerDeleteResponse:
    if is_builtin(retailer_id, RETAILERS):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Built-in retailer identities cannot be deleted from the demo foundry",
        )

    catalog = request.app.state.catalogs.get(retailer_id)
    if catalog is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown custom retailer: {retailer_id}",
        )

    await catalog.reset()
    await catalog.close()
    await request.app.state.redis.client.delete(f"demo:retailer:configuration:{retailer_id}")
    request.app.state.retailers.pop(retailer_id, None)
    request.app.state.catalogs.pop(retailer_id, None)
    request.app.state.evaluations.pop(retailer_id, None)
    request.app.state.telemetries.pop(retailer_id, None)
    return RetailerDeleteResponse(retailer_id=retailer_id)

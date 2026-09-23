from fastapi import APIRouter, Request

from app.models import RetailerDeleteResponse, RetailerImportRequest, RetailerImportResponse
from app.services.onboarding import delete_retailer, import_retailer

router = APIRouter()


@router.post(
    "/api/v1/retailers/import",
    response_model=RetailerImportResponse,
    tags=["configuration"],
)
async def create_retailer(
    request: Request, payload: RetailerImportRequest
) -> RetailerImportResponse:
    return await import_retailer(request, payload)


@router.delete(
    "/api/v1/retailers/{retailer_id}",
    response_model=RetailerDeleteResponse,
    tags=["configuration"],
)
async def remove_retailer(request: Request, retailer_id: str) -> RetailerDeleteResponse:
    return await delete_retailer(request, retailer_id)

from app.api.health import router as health_router
from app.api.onboarding import router as onboarding_router
from app.api.operations import router as operations_router
from app.api.search import router as search_router

__all__ = ["health_router", "onboarding_router", "operations_router", "search_router"]

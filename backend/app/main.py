import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health_router, operations_router, search_router
from app.config import Settings, get_settings
from app.evaluation import EvaluationService
from app.redis import RedisClient
from app.retrieval import CatalogService
from app.telemetry import TelemetryService


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = active_settings
        app.state.redis = RedisClient(active_settings)
        app.state.catalog = CatalogService(active_settings, app.state.redis.client)
        app.state.evaluation = EvaluationService(
            active_settings, app.state.redis.client, app.state.catalog
        )
        app.state.telemetry = TelemetryService(app.state.redis.client)
        try:
            yield
        finally:
            await app.state.catalog.close()
            await app.state.redis.close()

    app = FastAPI(
        title="GiftFind RedisVL Relevance Lab",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(active_settings.frontend_origin).rstrip("/")],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def add_request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started_at) * 1_000
            app.state.telemetry.record_request(status_code=500, duration_ms=duration_ms)
            logging.getLogger(__name__).exception(
                "request_failed",
                extra={"request_id": request_id, "path": request.url.path},
            )
            raise
        duration_ms = (time.perf_counter() - started_at) * 1_000
        app.state.telemetry.record_request(
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        logging.getLogger(__name__).info(
            json.dumps(
                {
                    "event": "request_completed",
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            )
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Server-Time-Ms"] = f"{duration_ms:.2f}"
        return response

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logging.getLogger(__name__).exception("Unhandled API error", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(health_router)
    app.include_router(search_router)
    app.include_router(operations_router)
    return app


configure_logging()
app = create_app()

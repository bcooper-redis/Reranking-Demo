from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


class AvailableRedis:
    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None


class UnavailableRedis:
    async def ping(self) -> bool:
        raise ConnectionError("redis unavailable")

    async def close(self) -> None:
        return None


def test_liveness_does_not_depend_on_redis() -> None:
    app = create_app(Settings())
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "giftfind-api"}


def test_readiness_reports_redis_connectivity() -> None:
    app = create_app(Settings())
    with TestClient(app) as client:
        app.state.redis = AvailableRedis()
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["redis"] == "connected"


def test_readiness_returns_503_when_redis_is_unavailable() -> None:
    app = create_app(Settings())
    with TestClient(app) as client:
        app.state.redis = UnavailableRedis()
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["redis"] == "unavailable"

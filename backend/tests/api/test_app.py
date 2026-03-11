from fastapi.testclient import TestClient

from app.core.exceptions import AppException
from app.main import create_app


def test_app_registers_routes() -> None:
    app = create_app()
    paths = {route.path for route in app.router.routes}

    assert "/api" not in paths
    assert "/ws/tasks" in paths


def test_app_handles_app_exception() -> None:
    app = create_app()

    @app.get("/api/test-error")
    async def raise_error() -> None:
        raise AppException(code="test_error", message="boom", status_code=409, details={"x": 1})

    client = TestClient(app)
    response = client.get("/api/test-error")

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "boom"
    assert body["data"]["code"] == "test_error"

"""Tests for app assembly: route registration, lifespan broadcaster, and WebSocket."""
from __future__ import annotations

from fastapi import Request, status
from fastapi.testclient import TestClient

from app.api.websocket import get_broadcaster
from app.main import create_app
from app.realtime.broadcaster import TaskBroadcaster


class TestRouteRegistration:
    """create_app() must expose all HTTP and WebSocket routes through assembly."""

    def _get_paths(self) -> set[str]:
        app = create_app()
        return {route.path for route in app.router.routes}

    def test_projects_routes(self) -> None:
        paths = self._get_paths()
        assert "/api/projects" in paths
        assert "/api/projects/{project_id}" in paths

    def test_systems_routes(self) -> None:
        paths = self._get_paths()
        assert "/api/projects/{project_id}/systems" in paths
        assert "/api/systems/{system_id}" in paths
        assert "/api/systems/{system_id}/advance" in paths
        assert "/api/systems/{system_id}/workflow" in paths

    def test_websocket_route(self) -> None:
        paths = self._get_paths()
        assert "/ws/tasks" in paths


class TestLifespanBroadcaster:
    """Lifespan must create broadcaster on app.state."""

    def test_broadcaster_available_during_lifespan(self) -> None:
        app = create_app()
        with TestClient(app) as client:
            broadcaster = getattr(app.state, "broadcaster", None)
            assert broadcaster is not None
            assert isinstance(broadcaster, TaskBroadcaster)
            # Verify the client is functional (health-check style)
            assert client is not None

    def test_broadcaster_requires_lifespan_started(self) -> None:
        app = create_app()
        request = Request(
            {
                "type": "http",
                "app": app,
                "headers": [],
                "method": "GET",
                "path": "/api/projects",
                "query_string": b"",
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
                "scheme": "http",
            }
        )

        try:
            get_broadcaster(request)
        except RuntimeError as exc:
            assert "lifespan may not have started" in str(exc)
        else:
            raise AssertionError("expected RuntimeError when lifespan is not started")


class TestHTTPEndpoints:
    """Smoke tests that HTTP endpoints are reachable through create_app() assembly."""

    def test_list_projects_reachable(self) -> None:
        """GET /api/projects should be routed (may 500 without DB, but not 404)."""
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/projects")
            # 404 means the route is not registered; anything else means it is
            assert response.status_code != status.HTTP_404_NOT_FOUND

    def test_create_project_reachable(self) -> None:
        """POST /api/projects should be routed."""
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/projects", json={"title": "t"})
            assert response.status_code != status.HTTP_404_NOT_FOUND

    def test_advance_system_reachable(self) -> None:
        """POST /api/systems/{id}/advance should be routed."""
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/systems/fake-id/advance")
            assert response.status_code != status.HTTP_404_NOT_FOUND

    def test_system_workflow_reachable(self) -> None:
        """GET /api/systems/{id}/workflow should be routed."""
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/systems/fake-id/workflow")
            assert response.status_code != status.HTTP_404_NOT_FOUND


class TestWebSocketEndpoint:
    """WebSocket /ws/tasks must be reachable through create_app()."""

    def test_websocket_connect(self) -> None:
        app = create_app()
        with TestClient(app) as client:
            with client.websocket_connect("/ws/tasks") as ws:
                # Connection accepted means the route is live and broadcaster is available
                assert ws is not None

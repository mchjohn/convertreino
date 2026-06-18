from uuid import uuid4

import pytest
from fastmcp.client import Client
from starlette.testclient import TestClient

from convertreino.api.main import create_app
from convertreino.infrastructure.repositories.in_memory_activity_repository import (
    InMemoryActivityRepository,
)
from convertreino.mcp.schemas import LongestRideResult
from convertreino.mcp.server import create_mcp_server, set_activity_repo_factory
from tests.builders import build_activity


@pytest.fixture(autouse=True)
def reset_activity_repo_factory():
    set_activity_repo_factory(None)
    yield
    set_activity_repo_factory(None)


@pytest.mark.anyio
async def test_mcp_server_invokes_get_longest_ride_in_process():
    # Arrange
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=120000)
    ]
    set_activity_repo_factory(lambda: InMemoryActivityRepository(activities))
    server = create_mcp_server()

    # Act
    async with Client(server) as client:
        result = await client.call_tool("get_longest_ride", {"user_id": str(user_id)})

    # Assert
    payload = LongestRideResult.model_validate(result.data)
    assert payload.distance_km == 120.0
    assert payload.activity_id is not None


def test_mcp_http_endpoint_is_mounted_on_fastapi():
    # Arrange
    set_activity_repo_factory(lambda: InMemoryActivityRepository([]))

    # Act
    with TestClient(create_app()) as client:
        response = client.get("/mcp")

    # Assert
    assert response.status_code == 406

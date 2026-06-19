from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastmcp.client import Client

from convertreino.domain.services.volume_engine import VolumeEngine
from convertreino.infrastructure.repositories.in_memory_activity_repository import (
    InMemoryActivityRepository,
)
from convertreino.mcp.schemas import RideVolumeResult
from convertreino.mcp.server import create_mcp_server, set_activity_repo_factory
from tests.builders import build_activity


@pytest.fixture(autouse=True)
def reset_activity_repo_factory():
    set_activity_repo_factory(None)
    yield
    set_activity_repo_factory(None)


def _configure_engine(activities: list) -> None:
    set_activity_repo_factory(lambda: InMemoryActivityRepository(activities))


async def _call_get_ride_volume(
    user_id,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> RideVolumeResult:
    payload: dict[str, str] = {"user_id": str(user_id)}
    if start_date is not None:
        payload["start_date"] = start_date.isoformat()
    if end_date is not None:
        payload["end_date"] = end_date.isoformat()
    server = create_mcp_server()
    async with Client(server) as client:
        result = await client.call_tool("get_ride_volume", payload)
    return RideVolumeResult.model_validate(result.data)


@pytest.mark.anyio
async def test_get_ride_volume_sums_distances_within_date_range():
    # Arrange — CN-1
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            activity_type="Ride",
            distance_meters=42000,
            start_date=datetime(2023, 1, 1, 8, 0, 0, tzinfo=UTC),
        ),
        build_activity(
            user_id=user_id,
            activity_type="Ride",
            distance_meters=5000,
            start_date=datetime(2024, 3, 1, 8, 0, 0, tzinfo=UTC),
        ),
        build_activity(
            user_id=user_id,
            activity_type="Ride",
            distance_meters=10000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_ride_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_km == 15.0
    assert result.activities_count == 2


@pytest.mark.anyio
async def test_get_ride_volume_returns_full_history_without_date_filter():
    # Arrange — CN-2
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=5000),
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=21097),
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=10000),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_ride_volume(user_id)

    # Assert
    assert result.total_distance_km == 36.097
    assert result.activities_count == 3


@pytest.mark.anyio
async def test_get_ride_volume_returns_zero_when_no_activities_in_range():
    # Arrange — CE-1
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            activity_type="Ride",
            distance_meters=10000,
            start_date=datetime(2023, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_ride_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_km == 0.0
    assert result.activities_count == 0


def test_get_ride_volume_handler_delegates_to_volume_engine():
    # Arrange
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=5000),
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=10000),
    ]
    engine = VolumeEngine(InMemoryActivityRepository(activities))

    # Act
    from convertreino.mcp.tools.volume import get_ride_volume

    result = get_ride_volume(user_id, engine)

    # Assert
    assert result.total_distance_km == 15.0
    assert result.activities_count == 2

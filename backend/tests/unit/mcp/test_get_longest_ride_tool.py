from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError

from convertreino.domain.services.pr_engine import PREngine
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


def _configure_engine(activities: list) -> None:
    set_activity_repo_factory(lambda: InMemoryActivityRepository(activities))


async def _call_get_longest_ride(user_id) -> LongestRideResult:
    server = create_mcp_server()
    async with Client(server) as client:
        result = await client.call_tool("get_longest_ride", {"user_id": str(user_id)})
    return LongestRideResult.model_validate(result.data)


@pytest.mark.anyio
async def test_get_longest_ride_returns_activity_with_max_distance():
    # Arrange — CN-1
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=30000),
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=120000),
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=80000),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_longest_ride(user_id)

    # Assert
    assert result.distance_km == 120.0
    assert result.activity_id is not None
    assert result.date is not None
    assert result.duration_minutes is not None


@pytest.mark.anyio
async def test_get_longest_ride_returns_single_ride():
    # Arrange — CN-2
    user_id = uuid4()
    activities = [build_activity(user_id=user_id, activity_type="Ride", distance_meters=65000)]
    _configure_engine(activities)

    # Act
    result = await _call_get_longest_ride(user_id)

    # Assert
    assert result.distance_km == 65.0
    assert result.activity_id is not None


@pytest.mark.anyio
async def test_get_longest_ride_returns_null_fields_when_no_rides():
    # Arrange — CB-1
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, activity_type="Run", distance_meters=10000),
        build_activity(user_id=user_id, activity_type="Swim", distance_meters=2000),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_longest_ride(user_id)

    # Assert
    assert result == LongestRideResult(
        activity_id=None,
        distance_km=None,
        date=None,
        duration_minutes=None,
        average_speed_kmh=None,
    )


@pytest.mark.anyio
async def test_get_longest_ride_breaks_distance_tie_by_most_recent_start_date():
    # Arrange — CB-2
    user_id = uuid4()
    older_ride = build_activity(
        user_id=user_id,
        activity_type="Ride",
        distance_meters=80000,
        start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
    )
    newer_ride = build_activity(
        user_id=user_id,
        activity_type="Ride",
        distance_meters=80000,
        start_date=datetime(2024, 9, 15, 7, 30, 0, tzinfo=UTC),
    )
    _configure_engine([older_ride, newer_ride])

    # Act
    result = await _call_get_longest_ride(user_id)

    # Assert
    assert result.activity_id == str(newer_ride.id)
    assert result.date == newer_ride.start_date.isoformat()


@pytest.mark.anyio
async def test_get_longest_ride_ignores_non_ride_activities_with_greater_distance():
    # Arrange — CB-3
    user_id = uuid4()
    ride = build_activity(user_id=user_id, activity_type="Ride", distance_meters=50000)
    run = build_activity(user_id=user_id, activity_type="Run", distance_meters=42195)
    _configure_engine([ride, run])

    # Act
    result = await _call_get_longest_ride(user_id)

    # Assert
    assert result.activity_id == str(ride.id)
    assert result.distance_km == 50.0


@pytest.mark.anyio
async def test_get_longest_ride_returns_null_speed_when_distance_is_zero():
    # Arrange — CB-4
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            activity_type="Ride",
            distance_meters=0,
            elapsed_time_seconds=600,
        )
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_longest_ride(user_id)

    # Assert
    assert result.distance_km == 0.0
    assert result.average_speed_kmh is None


@pytest.mark.anyio
async def test_get_longest_ride_returns_null_fields_when_user_has_no_activities():
    # Arrange — CE-1
    user_id = uuid4()
    _configure_engine([])

    # Act
    result = await _call_get_longest_ride(user_id)

    # Assert
    assert result == LongestRideResult(
        activity_id=None,
        distance_km=None,
        date=None,
        duration_minutes=None,
        average_speed_kmh=None,
    )


@pytest.mark.anyio
async def test_get_longest_ride_returns_null_fields_for_unknown_user_id():
    # Arrange — CE-2
    other_user_id = uuid4()
    activities = [
        build_activity(user_id=other_user_id, activity_type="Ride", distance_meters=50000)
    ]
    _configure_engine(activities)
    unknown_user_id = uuid4()

    # Act
    result = await _call_get_longest_ride(unknown_user_id)

    # Assert
    assert result == LongestRideResult(
        activity_id=None,
        distance_km=None,
        date=None,
        duration_minutes=None,
        average_speed_kmh=None,
    )


@pytest.mark.anyio
async def test_get_longest_ride_rejects_invalid_user_id():
    # Arrange — CE-3
    _configure_engine([])
    server = create_mcp_server()

    # Act / Assert
    async with Client(server) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_longest_ride", {"user_id": "not-a-uuid"})


def test_get_longest_ride_handler_delegates_to_pr_engine():
    # Arrange
    user_id = uuid4()
    activity = build_activity(user_id=user_id, activity_type="Ride", distance_meters=85000)
    engine = PREngine(InMemoryActivityRepository([activity]))

    # Act
    from convertreino.mcp.tools.pr import get_longest_ride

    result = get_longest_ride(user_id, engine)

    # Assert
    assert result.distance_km == 85.0
    assert result.activity_id == str(activity.id)

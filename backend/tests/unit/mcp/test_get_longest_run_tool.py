from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError

from convertreino.domain.services.pr_engine import PREngine
from convertreino.infrastructure.repositories.in_memory_activity_repository import (
    InMemoryActivityRepository,
)
from convertreino.mcp.schemas import LongestRunResult
from convertreino.mcp.server import create_mcp_server, set_activity_repo_factory
from tests.builders import build_activity


@pytest.fixture(autouse=True)
def reset_activity_repo_factory():
    set_activity_repo_factory(None)
    yield
    set_activity_repo_factory(None)


def _configure_engine(activities: list) -> None:
    set_activity_repo_factory(lambda: InMemoryActivityRepository(activities))


async def _call_get_longest_run(user_id) -> LongestRunResult:
    server = create_mcp_server()
    async with Client(server) as client:
        result = await client.call_tool("get_longest_run", {"user_id": str(user_id)})
    return LongestRunResult.model_validate(result.data)


@pytest.mark.anyio
async def test_get_longest_run_returns_activity_with_max_distance():
    # Arrange — CN-1
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, distance_meters=5000),
        build_activity(user_id=user_id, distance_meters=21097),
        build_activity(user_id=user_id, distance_meters=10000),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_longest_run(user_id)

    # Assert
    assert result.distance_km == 21.097
    assert result.activity_id is not None
    assert result.date is not None
    assert result.duration_minutes is not None


@pytest.mark.anyio
async def test_get_longest_run_returns_single_run():
    # Arrange — CN-2
    user_id = uuid4()
    activities = [build_activity(user_id=user_id, distance_meters=8420)]
    _configure_engine(activities)

    # Act
    result = await _call_get_longest_run(user_id)

    # Assert
    assert result.distance_km == 8.42
    assert result.activity_id is not None


@pytest.mark.anyio
async def test_get_longest_run_returns_null_fields_when_no_runs():
    # Arrange — CB-1
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=50000),
        build_activity(user_id=user_id, activity_type="Swim", distance_meters=2000),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_longest_run(user_id)

    # Assert
    assert result == LongestRunResult(
        activity_id=None,
        distance_km=None,
        date=None,
        duration_minutes=None,
        average_pace_min_per_km=None,
    )


@pytest.mark.anyio
async def test_get_longest_run_breaks_distance_tie_by_most_recent_start_date():
    # Arrange — CB-2
    user_id = uuid4()
    older_run = build_activity(
        user_id=user_id,
        distance_meters=10000,
        start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
    )
    newer_run = build_activity(
        user_id=user_id,
        distance_meters=10000,
        start_date=datetime(2024, 9, 15, 7, 30, 0, tzinfo=UTC),
    )
    _configure_engine([older_run, newer_run])

    # Act
    result = await _call_get_longest_run(user_id)

    # Assert
    assert result.activity_id == str(newer_run.id)
    assert result.date == newer_run.start_date.isoformat()


@pytest.mark.anyio
async def test_get_longest_run_ignores_non_run_activities_with_greater_distance():
    # Arrange — CB-3
    user_id = uuid4()
    run = build_activity(user_id=user_id, activity_type="Run", distance_meters=10000)
    ride = build_activity(user_id=user_id, activity_type="Ride", distance_meters=85000)
    _configure_engine([run, ride])

    # Act
    result = await _call_get_longest_run(user_id)

    # Assert
    assert result.activity_id == str(run.id)
    assert result.distance_km == 10.0


@pytest.mark.anyio
async def test_get_longest_run_returns_null_fields_when_user_has_no_activities():
    # Arrange — CE-1
    user_id = uuid4()
    _configure_engine([])

    # Act
    result = await _call_get_longest_run(user_id)

    # Assert
    assert result == LongestRunResult(
        activity_id=None,
        distance_km=None,
        date=None,
        duration_minutes=None,
        average_pace_min_per_km=None,
    )


@pytest.mark.anyio
async def test_get_longest_run_returns_null_fields_for_unknown_user_id():
    # Arrange — CE-2
    other_user_id = uuid4()
    activities = [build_activity(user_id=other_user_id, distance_meters=10000)]
    _configure_engine(activities)
    unknown_user_id = uuid4()

    # Act
    result = await _call_get_longest_run(unknown_user_id)

    # Assert
    assert result == LongestRunResult(
        activity_id=None,
        distance_km=None,
        date=None,
        duration_minutes=None,
        average_pace_min_per_km=None,
    )


@pytest.mark.anyio
async def test_get_longest_run_rejects_invalid_user_id():
    # Arrange — CE-3
    _configure_engine([])
    server = create_mcp_server()

    # Act / Assert
    async with Client(server) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_longest_run", {"user_id": "not-a-uuid"})


def test_get_longest_run_handler_delegates_to_pr_engine():
    # Arrange
    user_id = uuid4()
    activity = build_activity(user_id=user_id, distance_meters=15000)
    engine = PREngine(InMemoryActivityRepository([activity]))

    # Act
    from convertreino.mcp.tools.pr import get_longest_run

    result = get_longest_run(user_id, engine)

    # Assert
    assert result.distance_km == 15.0
    assert result.activity_id == str(activity.id)

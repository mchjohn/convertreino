from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError

from convertreino.domain.services.volume_engine import VolumeEngine
from convertreino.infrastructure.repositories.in_memory_activity_repository import (
    InMemoryActivityRepository,
)
from convertreino.mcp.schemas import RunVolumeResult
from convertreino.mcp.server import create_mcp_server, set_activity_repo_factory
from tests.builders import build_activity


@pytest.fixture(autouse=True)
def reset_activity_repo_factory():
    set_activity_repo_factory(None)
    yield
    set_activity_repo_factory(None)


def _configure_engine(activities: list) -> None:
    set_activity_repo_factory(lambda: InMemoryActivityRepository(activities))


async def _call_get_run_volume(
    user_id,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> RunVolumeResult:
    payload: dict[str, str] = {"user_id": str(user_id)}
    if start_date is not None:
        payload["start_date"] = start_date.isoformat()
    if end_date is not None:
        payload["end_date"] = end_date.isoformat()
    server = create_mcp_server()
    async with Client(server) as client:
        result = await client.call_tool("get_run_volume", payload)
    return RunVolumeResult.model_validate(result.data)


@pytest.mark.anyio
async def test_get_run_volume_sums_distances_within_date_range():
    # Arrange — CN-1
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            distance_meters=42000,
            start_date=datetime(2023, 1, 1, 8, 0, 0, tzinfo=UTC),
        ),
        build_activity(
            user_id=user_id,
            distance_meters=5000,
            start_date=datetime(2024, 3, 1, 8, 0, 0, tzinfo=UTC),
        ),
        build_activity(
            user_id=user_id,
            distance_meters=10000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_km == 15.0
    assert result.activities_count == 2


@pytest.mark.anyio
async def test_get_run_volume_returns_full_history_without_date_filter():
    # Arrange — CN-2
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, distance_meters=5000),
        build_activity(user_id=user_id, distance_meters=21097),
        build_activity(user_id=user_id, distance_meters=10000),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_run_volume(user_id)

    # Assert
    assert result.total_distance_km == 36.097
    assert result.activities_count == 3


@pytest.mark.anyio
async def test_get_run_volume_with_start_date_only_filters_lower_bound():
    # Arrange — CN-3
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            distance_meters=30000,
            start_date=datetime(2023, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
        build_activity(
            user_id=user_id,
            distance_meters=10000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_km == 10.0
    assert result.activities_count == 1


@pytest.mark.anyio
async def test_get_run_volume_with_end_date_only_filters_upper_bound():
    # Arrange — CN-4
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            distance_meters=80000,
            start_date=datetime(2023, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
        build_activity(
            user_id=user_id,
            distance_meters=120000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_run_volume(
        user_id,
        end_date=datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_km == 80.0
    assert result.activities_count == 1


@pytest.mark.anyio
async def test_get_run_volume_includes_activity_exactly_on_interval_boundary():
    # Arrange — CB-1
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            distance_meters=10000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_run_volume(
        user_id,
        start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_km == 10.0
    assert result.activities_count == 1


@pytest.mark.anyio
async def test_get_run_volume_returns_zero_when_only_wrong_activity_type_in_range():
    # Arrange — CB-2
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            activity_type="Ride",
            distance_meters=50000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_km == 0.0
    assert result.activities_count == 0


@pytest.mark.anyio
async def test_get_run_volume_isolates_run_from_mixed_activity_types():
    # Arrange — CB-3
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            activity_type="Ride",
            distance_meters=85000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
        build_activity(
            user_id=user_id,
            activity_type="Run",
            distance_meters=10000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_km == 10.0
    assert result.activities_count == 1


@pytest.mark.anyio
async def test_get_run_volume_counts_zero_distance_activities():
    # Arrange — CB-4
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            distance_meters=5000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
        build_activity(
            user_id=user_id,
            distance_meters=0,
            start_date=datetime(2024, 7, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_km == 5.0
    assert result.activities_count == 2


@pytest.mark.anyio
async def test_get_run_volume_returns_zero_when_no_activities_in_range():
    # Arrange — CE-1
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            distance_meters=10000,
            start_date=datetime(2023, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_km == 0.0
    assert result.activities_count == 0


@pytest.mark.anyio
async def test_get_run_volume_returns_zero_for_invalid_date_range():
    # Arrange — CE-2
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            distance_meters=10000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    _configure_engine(activities)

    # Act
    result = await _call_get_run_volume(
        user_id,
        start_date=datetime(2024, 12, 31, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_km == 0.0
    assert result.activities_count == 0


@pytest.mark.anyio
async def test_get_run_volume_returns_zero_when_user_has_no_activities():
    # Arrange — CE-3
    user_id = uuid4()
    _configure_engine([])

    # Act
    result = await _call_get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_km == 0.0
    assert result.activities_count == 0


@pytest.mark.anyio
async def test_get_run_volume_rejects_malformed_start_date():
    # Arrange — CE-4
    user_id = uuid4()
    _configure_engine([])
    server = create_mcp_server()

    # Act / Assert
    async with Client(server) as client:
        with pytest.raises(ToolError):
            await client.call_tool(
                "get_run_volume",
                {"user_id": str(user_id), "start_date": "not-a-date"},
            )


def test_get_run_volume_handler_delegates_to_volume_engine():
    # Arrange
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, distance_meters=5000),
        build_activity(user_id=user_id, distance_meters=10000),
    ]
    engine = VolumeEngine(InMemoryActivityRepository(activities))

    # Act
    from convertreino.mcp.tools.volume import get_run_volume

    result = get_run_volume(user_id, engine)

    # Assert
    assert result.total_distance_km == 15.0
    assert result.activities_count == 2

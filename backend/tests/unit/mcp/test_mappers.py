from datetime import UTC, datetime
from uuid import uuid4

from convertreino.mcp.mappers import activity_to_longest_ride_result, activity_to_longest_run_result
from convertreino.mcp.schemas import LongestRideResult, LongestRunResult
from tests.builders import build_activity


def test_activity_to_longest_run_result_returns_all_null_when_activity_is_none():
    # Arrange / Act
    result = activity_to_longest_run_result(None)

    # Assert
    assert result == LongestRunResult(
        activity_id=None,
        distance_km=None,
        date=None,
        duration_minutes=None,
        average_pace_min_per_km=None,
    )


def test_activity_to_longest_run_result_maps_activity_fields():
    # Arrange
    activity_id = uuid4()
    start_date = datetime(2024, 9, 15, 7, 30, 0, tzinfo=UTC)
    activity = build_activity(
        id=activity_id,
        distance_meters=21097,
        elapsed_time_seconds=6300,
        start_date=start_date,
    )

    # Act
    result = activity_to_longest_run_result(activity)

    # Assert
    assert result.activity_id == str(activity_id)
    assert result.distance_km == 21.097
    assert result.date == start_date.isoformat()
    assert result.duration_minutes == 105.0
    assert result.average_pace_min_per_km == 4.98


def test_activity_to_longest_run_result_returns_null_pace_when_distance_is_zero():
    # Arrange
    activity = build_activity(distance_meters=0, elapsed_time_seconds=600)

    # Act
    result = activity_to_longest_run_result(activity)

    # Assert
    assert result.distance_km == 0.0
    assert result.average_pace_min_per_km is None


def test_activity_to_longest_ride_result_returns_all_null_when_activity_is_none():
    # Arrange / Act
    result = activity_to_longest_ride_result(None)

    # Assert
    assert result == LongestRideResult(
        activity_id=None,
        distance_km=None,
        date=None,
        duration_minutes=None,
        average_speed_kmh=None,
    )


def test_activity_to_longest_ride_result_maps_average_speed():
    # Arrange
    activity = build_activity(
        activity_type="Ride",
        distance_meters=120000,
        elapsed_time_seconds=14400,
    )

    # Act
    result = activity_to_longest_ride_result(activity)

    # Assert
    assert result.distance_km == 120.0
    assert result.average_speed_kmh == 30.0


def test_activity_to_longest_ride_result_maps_activity_fields():
    # Arrange
    activity_id = uuid4()
    start_date = datetime(2024, 9, 15, 7, 30, 0, tzinfo=UTC)
    activity = build_activity(
        id=activity_id,
        activity_type="Ride",
        distance_meters=65000,
        elapsed_time_seconds=9000,
        start_date=start_date,
    )

    # Act
    result = activity_to_longest_ride_result(activity)

    # Assert
    assert result.activity_id == str(activity_id)
    assert result.distance_km == 65.0
    assert result.date == start_date.isoformat()
    assert result.duration_minutes == 150.0
    assert result.average_speed_kmh == 26.0


def test_activity_to_longest_ride_result_returns_null_speed_when_distance_is_zero():
    # Arrange
    activity = build_activity(
        activity_type="Ride",
        distance_meters=0,
        elapsed_time_seconds=600,
    )

    # Act
    result = activity_to_longest_ride_result(activity)

    # Assert
    assert result.distance_km == 0.0
    assert result.average_speed_kmh is None

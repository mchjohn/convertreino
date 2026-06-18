from datetime import UTC, datetime
from uuid import uuid4

from convertreino.domain.services.volume_engine import VolumeEngine, VolumeResult
from convertreino.infrastructure.repositories.in_memory_activity_repository import (
    InMemoryActivityRepository,
)
from tests.builders import build_activity


def test_volume_engine_accepts_activity_repository_and_returns_volume_result():
    # Arrange / Act
    engine = VolumeEngine(InMemoryActivityRepository())
    result = engine.get_run_volume(uuid4())

    # Assert
    assert isinstance(engine, VolumeEngine)
    assert isinstance(result, VolumeResult)


def test_get_run_volume_sums_distances_within_date_range():
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
    engine = VolumeEngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_meters == 15000
    assert result.activities_count == 2


def test_get_run_volume_sums_full_history_without_date_filter():
    # Arrange — CN-2
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, distance_meters=5000),
        build_activity(user_id=user_id, distance_meters=21097),
        build_activity(user_id=user_id, distance_meters=10000),
    ]
    engine = VolumeEngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_run_volume(user_id)

    # Assert
    assert result.total_distance_meters == 36097
    assert result.activities_count == 3


def test_get_run_volume_with_start_date_only_filters_lower_bound():
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
    engine = VolumeEngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_meters == 10000
    assert result.activities_count == 1


def test_get_ride_volume_with_end_date_only_filters_upper_bound():
    # Arrange — CN-4
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            activity_type="Ride",
            distance_meters=80000,
            start_date=datetime(2023, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
        build_activity(
            user_id=user_id,
            activity_type="Ride",
            distance_meters=120000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    engine = VolumeEngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_ride_volume(
        user_id,
        end_date=datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_meters == 80000
    assert result.activities_count == 1


def test_get_run_volume_includes_activity_on_inclusive_date_boundaries():
    # Arrange — CB-1
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            distance_meters=10000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    engine = VolumeEngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_run_volume(
        user_id,
        start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_meters == 10000
    assert result.activities_count == 1


def test_get_run_volume_returns_zero_when_interval_has_no_matching_type():
    # Arrange — CB-2
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            activity_type="Ride",
            distance_meters=85000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    engine = VolumeEngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_meters == 0
    assert result.activities_count == 0


def test_get_run_volume_isolates_type_within_mixed_activities():
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
            start_date=datetime(2024, 7, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    engine = VolumeEngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_meters == 10000
    assert result.activities_count == 1


def test_get_run_volume_counts_zero_distance_activities():
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
    engine = VolumeEngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_meters == 5000
    assert result.activities_count == 2


def test_get_run_volume_returns_zero_when_no_activities_in_date_range():
    # Arrange — CE-1
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            distance_meters=10000,
            start_date=datetime(2023, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    engine = VolumeEngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_run_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_meters == 0
    assert result.activities_count == 0


def test_get_run_volume_returns_zero_for_invalid_date_range():
    # Arrange — CE-2
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            distance_meters=10000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    engine = VolumeEngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_run_volume(
        user_id,
        start_date=datetime(2024, 12, 31, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_meters == 0
    assert result.activities_count == 0


def test_get_ride_volume_returns_zero_when_user_has_no_activities():
    # Arrange — CE-3
    user_id = uuid4()
    engine = VolumeEngine(InMemoryActivityRepository())

    # Act
    result = engine.get_ride_volume(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    # Assert
    assert result.total_distance_meters == 0
    assert result.activities_count == 0


def test_get_ride_volume_sums_full_history_without_date_filter():
    # Arrange — subset crítico Ride (espelho CN-2)
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=30000),
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=120000),
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=80000),
    ]
    engine = VolumeEngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_ride_volume(user_id)

    # Assert
    assert result.total_distance_meters == 230000
    assert result.activities_count == 3

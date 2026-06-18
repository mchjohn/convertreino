from datetime import UTC, datetime
from uuid import uuid4

from convertreino.domain.entities.activity import Activity
from convertreino.domain.services.pr_engine import PREngine
from convertreino.infrastructure.repositories.in_memory_activity_repository import (
    InMemoryActivityRepository,
)
from tests.builders import build_activity


def test_pr_engine_accepts_activity_repository():
    # Arrange / Act
    engine = PREngine(InMemoryActivityRepository())

    # Assert
    assert isinstance(engine, PREngine)


def test_get_longest_run_returns_activity_with_max_distance():
    # Arrange — CN-1
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, distance_meters=5000),
        build_activity(user_id=user_id, distance_meters=21097),
        build_activity(user_id=user_id, distance_meters=10000),
    ]
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_run(user_id)

    # Assert
    assert result is not None
    assert isinstance(result, Activity)
    assert result.distance_meters == 21097


def test_get_longest_run_returns_single_run():
    # Arrange — CN-2
    user_id = uuid4()
    activities = [build_activity(user_id=user_id, distance_meters=8420)]
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_run(user_id)

    # Assert
    assert result is not None
    assert result.distance_meters == 8420


def test_get_longest_run_returns_none_when_no_runs():
    # Arrange — CB-1
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=50000),
        build_activity(user_id=user_id, activity_type="Swim", distance_meters=2000),
    ]
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_run(user_id)

    # Assert
    assert result is None


def test_get_longest_run_breaks_distance_tie_by_most_recent_start_date():
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
    engine = PREngine(InMemoryActivityRepository([older_run, newer_run]))

    # Act
    result = engine.get_longest_run(user_id)

    # Assert
    assert result is not None
    assert result.id == newer_run.id
    assert result.start_date == newer_run.start_date


def test_get_longest_run_ignores_non_run_activities_with_greater_distance():
    # Arrange — CB-3
    user_id = uuid4()
    run = build_activity(user_id=user_id, activity_type="Run", distance_meters=10000)
    ride = build_activity(user_id=user_id, activity_type="Ride", distance_meters=85000)
    engine = PREngine(InMemoryActivityRepository([run, ride]))

    # Act
    result = engine.get_longest_run(user_id)

    # Assert
    assert result is not None
    assert result.id == run.id
    assert result.distance_meters == 10000


def test_get_longest_run_returns_none_when_user_has_no_activities():
    # Arrange — CE-1
    user_id = uuid4()
    engine = PREngine(InMemoryActivityRepository())

    # Act
    result = engine.get_longest_run(user_id)

    # Assert
    assert result is None


def test_get_longest_run_returns_none_for_unknown_user_id():
    # Arrange — CE-2
    other_user_id = uuid4()
    activities = [build_activity(user_id=other_user_id, distance_meters=10000)]
    engine = PREngine(InMemoryActivityRepository(activities))
    unknown_user_id = uuid4()

    # Act
    result = engine.get_longest_run(unknown_user_id)

    # Assert
    assert result is None


def test_get_longest_ride_returns_activity_with_max_distance():
    # Arrange — CN-1
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=30000),
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=120000),
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=80000),
    ]
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_ride(user_id)

    # Assert
    assert result is not None
    assert isinstance(result, Activity)
    assert result.distance_meters == 120000


def test_get_longest_ride_returns_single_ride():
    # Arrange — CN-2
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, activity_type="Ride", distance_meters=65000),
    ]
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_ride(user_id)

    # Assert
    assert result is not None
    assert result.distance_meters == 65000


def test_get_longest_ride_returns_none_when_no_rides():
    # Arrange — CB-1
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, activity_type="Run", distance_meters=10000),
        build_activity(user_id=user_id, activity_type="Swim", distance_meters=2000),
    ]
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_ride(user_id)

    # Assert
    assert result is None


def test_get_longest_ride_breaks_distance_tie_by_most_recent_start_date():
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
    engine = PREngine(InMemoryActivityRepository([older_ride, newer_ride]))

    # Act
    result = engine.get_longest_ride(user_id)

    # Assert
    assert result is not None
    assert result.id == newer_ride.id
    assert result.start_date == newer_ride.start_date


def test_get_longest_ride_ignores_non_ride_activities_with_greater_distance():
    # Arrange — CB-3
    user_id = uuid4()
    ride = build_activity(user_id=user_id, activity_type="Ride", distance_meters=50000)
    run = build_activity(user_id=user_id, activity_type="Run", distance_meters=42195)
    engine = PREngine(InMemoryActivityRepository([ride, run]))

    # Act
    result = engine.get_longest_ride(user_id)

    # Assert
    assert result is not None
    assert result.id == ride.id
    assert result.distance_meters == 50000


def test_get_longest_ride_returns_none_when_user_has_no_activities():
    # Arrange — CE-1
    user_id = uuid4()
    engine = PREngine(InMemoryActivityRepository())

    # Act
    result = engine.get_longest_ride(user_id)

    # Assert
    assert result is None


def test_get_longest_ride_returns_none_for_unknown_user_id():
    # Arrange — CE-2
    other_user_id = uuid4()
    activities = [
        build_activity(user_id=other_user_id, activity_type="Ride", distance_meters=50000),
    ]
    engine = PREngine(InMemoryActivityRepository(activities))
    unknown_user_id = uuid4()

    # Act
    result = engine.get_longest_ride(unknown_user_id)

    # Assert
    assert result is None


def test_get_longest_run_returns_max_distance_within_date_range():
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
            distance_meters=15000,
            start_date=datetime(2024, 3, 1, 8, 0, 0, tzinfo=UTC),
        ),
        build_activity(
            user_id=user_id,
            distance_meters=25000,
            start_date=datetime(2024, 8, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_run(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result is not None
    assert result.distance_meters == 25000
    assert result.start_date == datetime(2024, 8, 1, 8, 0, 0, tzinfo=UTC)


def test_get_longest_run_with_start_date_only_filters_lower_bound():
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
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_run(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    # Assert
    assert result is not None
    assert result.distance_meters == 10000
    assert result.start_date == datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC)


def test_get_longest_ride_with_end_date_only_filters_upper_bound():
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
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_ride(
        user_id,
        end_date=datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result is not None
    assert result.distance_meters == 80000
    assert result.start_date == datetime(2023, 6, 1, 8, 0, 0, tzinfo=UTC)


def test_get_longest_run_includes_activity_on_inclusive_date_boundaries():
    # Arrange — CB-1
    user_id = uuid4()
    boundary_run = build_activity(
        user_id=user_id,
        distance_meters=10000,
        start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
    )
    engine = PREngine(InMemoryActivityRepository([boundary_run]))

    # Act
    result = engine.get_longest_run(
        user_id,
        start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
    )

    # Assert
    assert result is not None
    assert result.id == boundary_run.id


def test_get_longest_run_returns_none_when_interval_has_no_matching_type():
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
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_run(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result is None


def test_get_longest_run_breaks_distance_tie_within_date_range_by_most_recent_start_date():
    # Arrange — CB-3
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
    engine = PREngine(InMemoryActivityRepository([older_run, newer_run]))

    # Act
    result = engine.get_longest_run(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result is not None
    assert result.id == newer_run.id


def test_get_longest_run_ignores_other_types_within_date_range():
    # Arrange — CB-4
    user_id = uuid4()
    run = build_activity(
        user_id=user_id,
        activity_type="Run",
        distance_meters=10000,
        start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
    )
    ride = build_activity(
        user_id=user_id,
        activity_type="Ride",
        distance_meters=85000,
        start_date=datetime(2024, 7, 1, 8, 0, 0, tzinfo=UTC),
    )
    engine = PREngine(InMemoryActivityRepository([run, ride]))

    # Act
    result = engine.get_longest_run(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result is not None
    assert result.id == run.id
    assert result.distance_meters == 10000


def test_get_longest_run_returns_none_when_no_activities_in_date_range():
    # Arrange — CE-1
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            distance_meters=10000,
            start_date=datetime(2023, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_run(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
    )

    # Assert
    assert result is None


def test_get_longest_run_returns_none_for_invalid_date_range():
    # Arrange — CE-2
    user_id = uuid4()
    activities = [
        build_activity(
            user_id=user_id,
            distance_meters=10000,
            start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
        ),
    ]
    engine = PREngine(InMemoryActivityRepository(activities))

    # Act
    result = engine.get_longest_run(
        user_id,
        start_date=datetime(2024, 12, 31, 0, 0, 0, tzinfo=UTC),
        end_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    # Assert
    assert result is None


def test_get_longest_ride_returns_none_when_user_has_no_activities_with_start_date_filter():
    # Arrange — CE-3
    user_id = uuid4()
    engine = PREngine(InMemoryActivityRepository())

    # Act
    result = engine.get_longest_ride(
        user_id,
        start_date=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    # Assert
    assert result is None


def test_get_longest_run_normalizes_naive_date_parameters_to_utc():
    # Arrange
    user_id = uuid4()
    run = build_activity(
        user_id=user_id,
        distance_meters=10000,
        start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
    )
    engine = PREngine(InMemoryActivityRepository([run]))

    # Act
    result = engine.get_longest_run(
        user_id,
        start_date=datetime(2024, 6, 1, 8, 0, 0),
        end_date=datetime(2024, 6, 1, 8, 0, 0),
    )

    # Assert
    assert result is not None
    assert result.id == run.id

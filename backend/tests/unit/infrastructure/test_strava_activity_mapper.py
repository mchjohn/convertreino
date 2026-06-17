from uuid import uuid4

from convertreino.infrastructure.strava.client import StravaActivitySummary
from convertreino.infrastructure.strava.mapper import map_strava_activity_to_domain
from tests.builders import build_strava_activity_summary


def test_maps_valid_summary_to_activity():
    # Arrange
    user_id = uuid4()
    summary = build_strava_activity_summary(id=42, distance=5000.0, elapsed_time=1800)

    # Act
    activity = map_strava_activity_to_domain(summary, user_id=user_id)

    # Assert
    assert activity is not None
    assert activity.external_id == "42"
    assert activity.user_id == user_id
    assert activity.distance_meters == 5000.0
    assert activity.elapsed_time_seconds == 1800
    assert activity.activity_type == "Run"


def test_defaults_distance_to_zero_when_missing():
    # Arrange
    summary = StravaActivitySummary(
        id=1,
        start_date="2024-01-15T10:00:00Z",
        type="Run",
    )

    # Act
    activity = map_strava_activity_to_domain(summary, user_id=uuid4())

    # Assert
    assert activity is not None
    assert activity.distance_meters == 0.0


def test_uses_moving_time_when_elapsed_time_missing():
    # Arrange
    summary = build_strava_activity_summary(id=2, elapsed_time=None, moving_time=900)

    # Act
    activity = map_strava_activity_to_domain(summary, user_id=uuid4())

    # Assert
    assert activity is not None
    assert activity.elapsed_time_seconds == 900


def test_returns_none_for_negative_distance():
    # Arrange
    summary = build_strava_activity_summary(id=3, distance=-1.0)

    # Act
    activity = map_strava_activity_to_domain(summary, user_id=uuid4())

    # Assert
    assert activity is None


def test_returns_none_for_missing_type():
    # Arrange
    summary = StravaActivitySummary(
        id=4,
        start_date="2024-01-15T10:00:00Z",
        type="",
    )

    # Act
    activity = map_strava_activity_to_domain(summary, user_id=uuid4())

    # Assert
    assert activity is None


def test_returns_none_for_invalid_start_date():
    # Arrange
    summary = build_strava_activity_summary(id=5, start_date="not-a-date")

    # Act
    activity = map_strava_activity_to_domain(summary, user_id=uuid4())

    # Assert
    assert activity is None

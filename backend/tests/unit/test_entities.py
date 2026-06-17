from datetime import datetime

from tests.builders import build_activity, build_user


def test_user_normalizes_naive_created_at_to_utc():
    # Arrange
    naive = datetime(2026, 1, 15, 10, 0, 0)

    # Act
    user = build_user(created_at=naive)

    # Assert
    assert user.created_at.tzinfo is not None
    assert user.created_at.utcoffset() is not None


def test_activity_normalizes_naive_start_date_to_utc():
    # Arrange
    naive = datetime(2026, 1, 15, 10, 0, 0)

    # Act
    activity = build_activity(start_date=naive)

    # Assert
    assert activity.start_date.tzinfo is not None
    assert activity.start_date.utcoffset() is not None

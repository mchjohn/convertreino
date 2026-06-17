from uuid import uuid4

import pytest

from convertreino.domain.exceptions import DomainValidationError
from convertreino.infrastructure.repositories.in_memory_activity_repository import (
    InMemoryActivityRepository,
)
from convertreino.infrastructure.repositories.in_memory_user_repository import (
    InMemoryUserRepository,
)
from tests.builders import build_activity, build_user


def test_save_new_user_persists_and_preserves_id():
    # Arrange
    repo = InMemoryUserRepository()
    user = build_user()

    # Act
    result = repo.save(user)

    # Assert
    assert result.id == user.id
    assert repo.get_by_id(user.id) == user


def test_get_all_returns_two_activities_for_user():
    # Arrange
    user_id = uuid4()
    activities = [
        build_activity(user_id=user_id, distance_meters=5000),
        build_activity(user_id=user_id, distance_meters=10000),
    ]
    repo = InMemoryActivityRepository(activities)

    # Act
    result = repo.get_all(user_id)

    # Assert
    assert len(result) == 2
    distances = {activity.distance_meters for activity in result}
    assert distances == {5000.0, 10000.0}


def test_get_all_returns_empty_list_when_user_has_no_activities():
    # Arrange
    repo = InMemoryActivityRepository()

    # Act
    result = repo.get_all(uuid4())

    # Assert
    assert result == []


def test_save_accepts_activity_with_zero_distance():
    # Arrange
    repo = InMemoryActivityRepository()
    activity = build_activity(distance_meters=0)

    # Act
    result = repo.save(activity)

    # Assert
    assert result.distance_meters == 0
    assert repo.get_all(activity.user_id) == [activity]


def test_save_accepts_activity_without_external_id():
    # Arrange
    repo = InMemoryActivityRepository()
    activity = build_activity(external_id=None)

    # Act
    result = repo.save(activity)

    # Assert
    assert result.external_id is None
    assert repo.get_all(activity.user_id)[0].external_id is None


def test_activity_rejects_negative_distance():
    # Arrange
    user_id = uuid4()

    # Act / Assert
    with pytest.raises(DomainValidationError, match="distance_meters"):
        build_activity(user_id=user_id, distance_meters=-1)


def test_activity_rejects_negative_elapsed_time():
    # Arrange
    user_id = uuid4()

    # Act / Assert
    with pytest.raises(DomainValidationError, match="elapsed_time_seconds"):
        build_activity(user_id=user_id, elapsed_time_seconds=-1)


def test_get_by_id_returns_none_for_unknown_user():
    # Arrange
    repo = InMemoryUserRepository()

    # Act
    result = repo.get_by_id(uuid4())

    # Assert
    assert result is None

import inspect
from uuid import UUID

from convertreino.domain.entities.activity import Activity
from convertreino.domain.entities.user import User
from convertreino.domain.repositories.activity_repository import ActivityRepository
from convertreino.domain.repositories.user_repository import UserRepository


def test_user_repository_contract():
    # Arrange
    get_by_id = UserRepository.get_by_id
    get_by_strava_athlete_id = UserRepository.get_by_strava_athlete_id
    save = UserRepository.save

    # Assert
    assert inspect.isabstract(UserRepository)
    assert get_by_id.__annotations__["user_id"] is UUID
    assert get_by_id.__annotations__["return"] == User | None
    assert get_by_strava_athlete_id.__annotations__["athlete_id"] is int
    assert get_by_strava_athlete_id.__annotations__["return"] == User | None
    assert save.__annotations__["user"] is User
    assert save.__annotations__["return"] is User


def test_activity_repository_contract():
    # Arrange
    get_all = ActivityRepository.get_all
    save = ActivityRepository.save
    get_by_external_id = ActivityRepository.get_by_external_id
    upsert = ActivityRepository.upsert
    delete_by_external_id = ActivityRepository.delete_by_external_id

    # Assert
    assert inspect.isabstract(ActivityRepository)
    assert get_all.__annotations__["user_id"] is UUID
    assert get_all.__annotations__["return"] == list[Activity]
    assert save.__annotations__["activity"] is Activity
    assert save.__annotations__["return"] is Activity
    assert get_by_external_id.__annotations__["user_id"] is UUID
    assert get_by_external_id.__annotations__["external_id"] is str
    assert get_by_external_id.__annotations__["return"] == Activity | None
    assert upsert.__annotations__["activity"] is Activity
    assert upsert.__annotations__["return"] is Activity
    assert delete_by_external_id.__annotations__["user_id"] is UUID
    assert delete_by_external_id.__annotations__["external_id"] is str
    assert delete_by_external_id.__annotations__["return"] is bool

import inspect
from uuid import UUID

from convertreino.domain.entities.activity import Activity
from convertreino.domain.entities.user import User
from convertreino.domain.repositories.activity_repository import ActivityRepository
from convertreino.domain.repositories.user_repository import UserRepository


def test_user_repository_contract():
    # Arrange
    get_by_id = UserRepository.get_by_id
    save = UserRepository.save

    # Assert
    assert inspect.isabstract(UserRepository)
    assert get_by_id.__annotations__["user_id"] is UUID
    assert get_by_id.__annotations__["return"] == User | None
    assert save.__annotations__["user"] is User
    assert save.__annotations__["return"] is User


def test_activity_repository_contract():
    # Arrange
    get_all = ActivityRepository.get_all
    save = ActivityRepository.save

    # Assert
    assert inspect.isabstract(ActivityRepository)
    assert get_all.__annotations__["user_id"] is UUID
    assert get_all.__annotations__["return"] == list[Activity]
    assert save.__annotations__["activity"] is Activity
    assert save.__annotations__["return"] is Activity

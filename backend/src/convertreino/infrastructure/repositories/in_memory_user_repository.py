from uuid import UUID

from convertreino.domain.entities.user import User
from convertreino.domain.repositories.user_repository import UserRepository


class InMemoryUserRepository(UserRepository):
    def __init__(self, users: list[User] | None = None) -> None:
        self._store: dict[UUID, User] = {user.id: user for user in (users or [])}

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._store.get(user_id)

    def save(self, user: User) -> User:
        self._store[user.id] = user
        return user

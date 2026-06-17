from abc import ABC, abstractmethod
from uuid import UUID

from convertreino.domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: UUID) -> User | None:
        ...

    @abstractmethod
    def save(self, user: User) -> User:
        ...

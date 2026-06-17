from uuid import UUID

from sqlalchemy.orm import Session

from convertreino.domain.entities.user import User
from convertreino.domain.repositories.user_repository import UserRepository
from convertreino.infrastructure.db.models import UserModel


def _to_domain(model: UserModel) -> User:
    return User(id=model.id, created_at=model.created_at)


def _to_model(user: User) -> UserModel:
    return UserModel(id=user.id, created_at=user.created_at)


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: UUID) -> User | None:
        model = self._session.get(UserModel, user_id)
        if model is None:
            return None
        return _to_domain(model)

    def save(self, user: User) -> User:
        existing = self._session.get(UserModel, user.id)
        if existing is None:
            self._session.add(_to_model(user))
        else:
            existing.created_at = user.created_at
        self._session.flush()
        return user

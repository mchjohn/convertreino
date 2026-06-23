from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from convertreino.domain.entities.user import User
from convertreino.domain.exceptions import DomainIntegrityError
from convertreino.domain.repositories.user_repository import UserRepository
from convertreino.infrastructure.db.models import UserModel


def _to_domain(model: UserModel) -> User:
    return User(
        id=model.id,
        created_at=model.created_at,
        strava_athlete_id=model.strava_athlete_id,
        access_token=model.access_token,
        refresh_token=model.refresh_token,
        token_expires_at=model.token_expires_at,
    )


def _to_model(user: User) -> UserModel:
    return UserModel(
        id=user.id,
        created_at=user.created_at,
        strava_athlete_id=user.strava_athlete_id,
        access_token=user.access_token,
        refresh_token=user.refresh_token,
        token_expires_at=user.token_expires_at,
    )


def _apply_to_model(model: UserModel, user: User) -> None:
    model.created_at = user.created_at
    model.strava_athlete_id = user.strava_athlete_id
    model.access_token = user.access_token
    model.refresh_token = user.refresh_token
    model.token_expires_at = user.token_expires_at


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: UUID) -> User | None:
        model = self._session.get(UserModel, user_id)
        if model is None:
            return None
        return _to_domain(model)

    def get_by_strava_athlete_id(self, athlete_id: int) -> User | None:
        stmt = select(UserModel).where(UserModel.strava_athlete_id == athlete_id)
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return _to_domain(model)

    def save(self, user: User) -> User:
        existing = self._session.get(UserModel, user.id)
        if existing is None:
            self._session.add(_to_model(user))
        else:
            _apply_to_model(existing, user)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise DomainIntegrityError(
                f"strava_athlete_id {user.strava_athlete_id} violates uniqueness constraint"
            ) from exc
        return user

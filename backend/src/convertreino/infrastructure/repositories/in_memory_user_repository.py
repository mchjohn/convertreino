from uuid import UUID

from convertreino.domain.entities.user import User
from convertreino.domain.exceptions import DomainIntegrityError
from convertreino.domain.repositories.user_repository import UserRepository


class InMemoryUserRepository(UserRepository):
    def __init__(self, users: list[User] | None = None) -> None:
        self._store: dict[UUID, User] = {user.id: user for user in (users or [])}

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._store.get(user_id)

    def get_by_strava_athlete_id(self, athlete_id: int) -> User | None:
        for user in self._store.values():
            if user.strava_athlete_id == athlete_id:
                return user
        return None

    def save(self, user: User) -> User:
        if user.strava_athlete_id is not None:
            existing = self.get_by_strava_athlete_id(user.strava_athlete_id)
            if existing is not None and existing.id != user.id:
                raise DomainIntegrityError(
                    f"strava_athlete_id {user.strava_athlete_id} already linked to another user"
                )
        self._store[user.id] = user
        return user

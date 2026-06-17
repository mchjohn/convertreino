from uuid import UUID

from convertreino.domain.entities.activity import Activity
from convertreino.domain.repositories.activity_repository import ActivityRepository


class InMemoryActivityRepository(ActivityRepository):
    def __init__(self, activities: list[Activity] | None = None) -> None:
        self._store: dict[UUID, list[Activity]] = {}
        for activity in activities or []:
            self._store.setdefault(activity.user_id, []).append(activity)

    def get_all(self, user_id: UUID) -> list[Activity]:
        return list(self._store.get(user_id, []))

    def save(self, activity: Activity) -> Activity:
        self._store.setdefault(activity.user_id, []).append(activity)
        return activity

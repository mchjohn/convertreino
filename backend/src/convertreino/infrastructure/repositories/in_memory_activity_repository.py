from uuid import UUID

from convertreino.domain.entities.activity import Activity
from convertreino.domain.exceptions import DomainIntegrityError
from convertreino.domain.repositories.activity_repository import ActivityRepository


class InMemoryActivityRepository(ActivityRepository):
    def __init__(self, activities: list[Activity] | None = None) -> None:
        self._store: dict[UUID, list[Activity]] = {}
        for activity in activities or []:
            self._store.setdefault(activity.user_id, []).append(activity)

    def get_all(self, user_id: UUID) -> list[Activity]:
        return list(self._store.get(user_id, []))

    def save(self, activity: Activity) -> Activity:
        if activity.external_id is not None:
            existing = self.get_by_external_id(activity.user_id, activity.external_id)
            if existing is not None and existing.id != activity.id:
                raise DomainIntegrityError(
                    f"Duplicate external_id {activity.external_id} for user {activity.user_id}"
                )
        self._store.setdefault(activity.user_id, []).append(activity)
        return activity

    def get_by_external_id(self, user_id: UUID, external_id: str) -> Activity | None:
        for activity in self._store.get(user_id, []):
            if activity.external_id == external_id:
                return activity
        return None

    def upsert(self, activity: Activity) -> Activity:
        existing = (
            self.get_by_external_id(activity.user_id, activity.external_id)
            if activity.external_id is not None
            else None
        )
        if existing is not None:
            updated = Activity(
                id=existing.id,
                user_id=activity.user_id,
                distance_meters=activity.distance_meters,
                elapsed_time_seconds=activity.elapsed_time_seconds,
                start_date=activity.start_date,
                activity_type=activity.activity_type,
                external_id=activity.external_id,
            )
            activities = self._store[activity.user_id]
            index = activities.index(existing)
            activities[index] = updated
            return updated

        self._store.setdefault(activity.user_id, []).append(activity)
        return activity

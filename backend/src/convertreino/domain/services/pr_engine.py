from uuid import UUID

from convertreino.domain.entities.activity import Activity
from convertreino.domain.repositories.activity_repository import ActivityRepository


class PREngine:
    def __init__(self, activity_repo: ActivityRepository) -> None:
        self._activity_repo = activity_repo

    def get_longest_run(self, user_id: UUID) -> Activity | None:
        runs = [
            activity
            for activity in self._activity_repo.get_all(user_id)
            if activity.activity_type == "Run"
        ]
        if not runs:
            return None
        return max(runs, key=lambda activity: (activity.distance_meters, activity.start_date))

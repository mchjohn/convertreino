from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from convertreino.domain.repositories.activity_repository import ActivityRepository


@dataclass(frozen=True, slots=True)
class VolumeResult:
    total_distance_meters: float
    activities_count: int


class VolumeEngine:
    def __init__(self, activity_repo: ActivityRepository) -> None:
        self._activity_repo = activity_repo

    def get_run_volume(
        self,
        user_id: UUID,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> VolumeResult:
        return self._get_volume_by_type(
            user_id, "Run", start_date=start_date, end_date=end_date
        )

    def get_ride_volume(
        self,
        user_id: UUID,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> VolumeResult:
        return self._get_volume_by_type(
            user_id, "Ride", start_date=start_date, end_date=end_date
        )

    def _get_volume_by_type(
        self,
        user_id: UUID,
        activity_type: str,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> VolumeResult:
        normalized_start = _normalize_datetime(start_date)
        normalized_end = _normalize_datetime(end_date)

        if (
            normalized_start is not None
            and normalized_end is not None
            and normalized_start > normalized_end
        ):
            return VolumeResult(total_distance_meters=0, activities_count=0)

        activities = [
            activity
            for activity in self._activity_repo.get_all(user_id)
            if activity.activity_type == activity_type
        ]

        if normalized_start is not None:
            activities = [
                activity
                for activity in activities
                if activity.start_date >= normalized_start
            ]

        if normalized_end is not None:
            activities = [
                activity
                for activity in activities
                if activity.start_date <= normalized_end
            ]

        if not activities:
            return VolumeResult(total_distance_meters=0, activities_count=0)

        return VolumeResult(
            total_distance_meters=sum(activity.distance_meters for activity in activities),
            activities_count=len(activities),
        )


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value

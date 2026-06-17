from datetime import UTC, datetime
from uuid import UUID, uuid4

from convertreino.domain.entities.activity import Activity
from convertreino.domain.entities.user import User


def build_user(
    *,
    id: UUID | None = None,
    created_at: datetime | None = None,
) -> User:
    return User(
        id=id or uuid4(),
        created_at=created_at or datetime.now(UTC),
    )


def build_activity(
    *,
    id: UUID | None = None,
    user_id: UUID | None = None,
    distance_meters: float = 5000.0,
    elapsed_time_seconds: int = 1800,
    start_date: datetime | None = None,
    activity_type: str = "Run",
    external_id: str | None = None,
) -> Activity:
    return Activity(
        id=id or uuid4(),
        user_id=user_id or uuid4(),
        distance_meters=distance_meters,
        elapsed_time_seconds=elapsed_time_seconds,
        start_date=start_date or datetime.now(UTC),
        activity_type=activity_type,
        external_id=external_id,
    )

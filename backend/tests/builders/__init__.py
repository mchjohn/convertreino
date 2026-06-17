from datetime import UTC, datetime
from uuid import UUID, uuid4

from convertreino.domain.entities.activity import Activity
from convertreino.domain.entities.user import User
from convertreino.infrastructure.strava.client import StravaActivitySummary


def build_user(
    *,
    id: UUID | None = None,
    created_at: datetime | None = None,
    strava_athlete_id: int | None = None,
    access_token: str | None = None,
    refresh_token: str | None = None,
    token_expires_at: datetime | None = None,
) -> User:
    return User(
        id=id or uuid4(),
        created_at=created_at or datetime.now(UTC),
        strava_athlete_id=strava_athlete_id,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires_at=token_expires_at,
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


def build_strava_activity_summary(
    *,
    id: int = 1,
    distance: float = 5000.0,
    elapsed_time: int | None = 1800,
    moving_time: int | None = None,
    start_date: str = "2024-01-15T10:00:00Z",
    type: str = "Run",
) -> StravaActivitySummary:
    return StravaActivitySummary(
        id=id,
        distance=distance,
        elapsed_time=elapsed_time,
        moving_time=moving_time,
        start_date=start_date,
        type=type,
    )

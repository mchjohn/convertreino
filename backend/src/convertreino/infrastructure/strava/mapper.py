from datetime import UTC, datetime
from uuid import UUID, uuid4

from convertreino.domain.entities.activity import Activity
from convertreino.infrastructure.strava.client import StravaActivitySummary


def map_strava_activity_to_domain(
    summary: StravaActivitySummary,
    *,
    user_id: UUID,
) -> Activity | None:
    if not summary.start_date or not summary.type:
        return None

    distance_meters = float(summary.distance)
    if summary.elapsed_time is not None:
        elapsed_time_seconds = int(summary.elapsed_time)
    elif summary.moving_time is not None:
        elapsed_time_seconds = int(summary.moving_time)
    else:
        elapsed_time_seconds = 0

    if distance_meters < 0 or elapsed_time_seconds < 0:
        return None

    try:
        start_date = datetime.fromisoformat(summary.start_date.replace("Z", "+00:00"))
    except ValueError:
        return None

    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=UTC)

    return Activity(
        id=uuid4(),
        user_id=user_id,
        distance_meters=distance_meters,
        elapsed_time_seconds=elapsed_time_seconds,
        start_date=start_date,
        activity_type=summary.type,
        external_id=str(summary.id),
    )

from convertreino.domain.entities.activity import Activity
from convertreino.mcp.schemas import LongestRunResult


def activity_to_longest_run_result(activity: Activity | None) -> LongestRunResult:
    if activity is None:
        return LongestRunResult(
            activity_id=None,
            distance_km=None,
            date=None,
            duration_minutes=None,
            average_pace_min_per_km=None,
        )

    distance_km = round(activity.distance_meters / 1000, 3)
    duration_minutes = round(activity.elapsed_time_seconds / 60, 1)
    average_pace_min_per_km = None
    if distance_km > 0:
        average_pace_min_per_km = round(duration_minutes / distance_km, 2)

    return LongestRunResult(
        activity_id=str(activity.id),
        distance_km=distance_km,
        date=activity.start_date.isoformat(),
        duration_minutes=duration_minutes,
        average_pace_min_per_km=average_pace_min_per_km,
    )

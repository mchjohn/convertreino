from convertreino.domain.entities.activity import Activity
from convertreino.domain.services.volume_engine import VolumeResult
from convertreino.mcp.schemas import (
    LongestRideResult,
    LongestRunResult,
    RideVolumeResult,
    RunVolumeResult,
)


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


def activity_to_longest_ride_result(activity: Activity | None) -> LongestRideResult:
    if activity is None:
        return LongestRideResult(
            activity_id=None,
            distance_km=None,
            date=None,
            duration_minutes=None,
            average_speed_kmh=None,
        )

    distance_km = round(activity.distance_meters / 1000, 3)
    duration_minutes = round(activity.elapsed_time_seconds / 60, 1)
    average_speed_kmh = None
    if distance_km > 0:
        average_speed_kmh = round(distance_km / (duration_minutes / 60), 2)

    return LongestRideResult(
        activity_id=str(activity.id),
        distance_km=distance_km,
        date=activity.start_date.isoformat(),
        duration_minutes=duration_minutes,
        average_speed_kmh=average_speed_kmh,
    )


def volume_result_to_run_volume_result(result: VolumeResult) -> RunVolumeResult:
    return RunVolumeResult(
        total_distance_km=round(result.total_distance_meters / 1000, 3),
        activities_count=result.activities_count,
    )


def volume_result_to_ride_volume_result(result: VolumeResult) -> RideVolumeResult:
    return RideVolumeResult(
        total_distance_km=round(result.total_distance_meters / 1000, 3),
        activities_count=result.activities_count,
    )

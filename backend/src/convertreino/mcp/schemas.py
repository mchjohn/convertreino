from pydantic import BaseModel


class LongestRunResult(BaseModel):
    activity_id: str | None
    distance_km: float | None
    date: str | None
    duration_minutes: float | None
    average_pace_min_per_km: float | None


class LongestRideResult(BaseModel):
    activity_id: str | None
    distance_km: float | None
    date: str | None
    duration_minutes: float | None
    average_speed_kmh: float | None


class RunVolumeResult(BaseModel):
    total_distance_km: float
    activities_count: int


class RideVolumeResult(BaseModel):
    total_distance_km: float
    activities_count: int

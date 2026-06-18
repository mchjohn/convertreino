from pydantic import BaseModel


class LongestRunResult(BaseModel):
    activity_id: str | None
    distance_km: float | None
    date: str | None
    duration_minutes: float | None
    average_pace_min_per_km: float | None

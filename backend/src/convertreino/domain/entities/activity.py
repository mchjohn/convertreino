from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from convertreino.domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class Activity:
    id: UUID
    user_id: UUID
    distance_meters: float
    elapsed_time_seconds: int
    start_date: datetime
    activity_type: str
    external_id: str | None = None

    def __post_init__(self) -> None:
        if self.distance_meters < 0:
            raise DomainValidationError("distance_meters must be >= 0")
        if self.elapsed_time_seconds < 0:
            raise DomainValidationError("elapsed_time_seconds must be >= 0")
        if self.start_date.tzinfo is None:
            object.__setattr__(self, "start_date", self.start_date.replace(tzinfo=UTC))

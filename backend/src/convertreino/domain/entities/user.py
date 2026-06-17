from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    created_at: datetime
    strava_athlete_id: int | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            object.__setattr__(self, "created_at", self.created_at.replace(tzinfo=UTC))
        if self.token_expires_at is not None and self.token_expires_at.tzinfo is None:
            object.__setattr__(
                self,
                "token_expires_at",
                self.token_expires_at.replace(tzinfo=UTC),
            )

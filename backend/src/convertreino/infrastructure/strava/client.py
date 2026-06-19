from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StravaTokenResponse:
    access_token: str
    refresh_token: str
    expires_at: datetime
    athlete_id: int


@dataclass(frozen=True, slots=True)
class StravaAthlete:
    id: int


@dataclass(frozen=True, slots=True)
class StravaActivitySummary:
    id: int
    start_date: str
    type: str
    distance: float = 0.0
    elapsed_time: int | None = None
    moving_time: int | None = None


class StravaApiClient(Protocol):
    def exchange_code(self, code: str, *, redirect_uri: str | None = None) -> StravaTokenResponse: ...

    def refresh_token(self, refresh_token: str) -> StravaTokenResponse: ...

    def get_athlete(self, access_token: str) -> StravaAthlete: ...

    def list_activities(
        self,
        access_token: str,
        *,
        page: int = 1,
        per_page: int = 200,
    ) -> list[StravaActivitySummary]: ...

    def get_activity(self, access_token: str, activity_id: int) -> StravaActivitySummary: ...


def expires_at_from_unix(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=UTC)

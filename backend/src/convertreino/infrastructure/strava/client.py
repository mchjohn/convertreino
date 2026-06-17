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


class StravaApiClient(Protocol):
    def exchange_code(self, code: str) -> StravaTokenResponse: ...

    def refresh_token(self, refresh_token: str) -> StravaTokenResponse: ...

    def get_athlete(self, access_token: str) -> StravaAthlete: ...


def expires_at_from_unix(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=UTC)

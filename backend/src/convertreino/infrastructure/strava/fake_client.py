from convertreino.domain.exceptions import StravaApiError, StravaAuthError
from convertreino.infrastructure.strava.client import (
    StravaActivitySummary,
    StravaAthlete,
    StravaTokenResponse,
)


class FakeStravaApiClient:
    def __init__(
        self,
        *,
        athlete_id: int = 42_001,
        access_token: str = "fake-access-token",
        refresh_token: str = "fake-refresh-token",
        expires_at_unix: int = 4_000_000_000,
        fail_exchange: bool = False,
        fail_refresh: bool = False,
        fail_server_error: bool = False,
        activities: list[StravaActivitySummary] | None = None,
        fail_list_auth_pages: set[int] | None = None,
        fail_list_server_pages: set[int] | None = None,
    ) -> None:
        self._athlete_id = athlete_id
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._expires_at_unix = expires_at_unix
        self._fail_exchange = fail_exchange
        self._fail_refresh = fail_refresh
        self._fail_server_error = fail_server_error
        self._activities = list(activities or [])
        self._fail_list_auth_pages = fail_list_auth_pages or set()
        self._fail_list_server_pages = fail_list_server_pages or set()
        self.exchange_calls: list[str] = []
        self.refresh_calls: list[str] = []
        self.list_activities_calls: list[tuple[int, int]] = []

    def exchange_code(self, code: str) -> StravaTokenResponse:
        self.exchange_calls.append(code)
        if self._fail_server_error:
            raise StravaAuthError("Strava API unavailable: 503")
        if self._fail_exchange:
            raise StravaAuthError("Strava token request failed: 400")
        return self._token_response()

    def refresh_token(self, refresh_token: str) -> StravaTokenResponse:
        self.refresh_calls.append(refresh_token)
        if self._fail_server_error:
            raise StravaAuthError("Strava API unavailable: 503")
        if self._fail_refresh:
            raise StravaAuthError("Strava token request failed: 400")
        return StravaTokenResponse(
            access_token=f"{self._access_token}-refreshed",
            refresh_token=f"{self._refresh_token}-refreshed",
            expires_at=self._token_response().expires_at,
            athlete_id=self._athlete_id,
        )

    def get_athlete(self, access_token: str) -> StravaAthlete:
        return StravaAthlete(id=self._athlete_id)

    def list_activities(
        self,
        access_token: str,
        *,
        page: int = 1,
        per_page: int = 200,
    ) -> list[StravaActivitySummary]:
        self.list_activities_calls.append((page, per_page))
        if page in self._fail_list_auth_pages:
            raise StravaAuthError("Reauthorize Strava account")
        if page in self._fail_list_server_pages:
            raise StravaApiError("Strava API unavailable: 503")

        start = (page - 1) * per_page
        end = start + per_page
        return self._activities[start:end]

    def _token_response(self) -> StravaTokenResponse:
        from convertreino.infrastructure.strava.client import expires_at_from_unix

        return StravaTokenResponse(
            access_token=self._access_token,
            refresh_token=self._refresh_token,
            expires_at=expires_at_from_unix(self._expires_at_unix),
            athlete_id=self._athlete_id,
        )

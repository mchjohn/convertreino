import httpx

from convertreino.domain.exceptions import StravaAuthError
from convertreino.infrastructure.strava.client import (
    StravaAthlete,
    StravaTokenResponse,
    expires_at_from_unix,
)

STRAVA_OAUTH_URL = "https://www.strava.com/oauth/token"
STRAVA_ATHLETE_URL = "https://www.strava.com/api/v3/athlete"


class HttpxStravaApiClient:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    def exchange_code(self, code: str) -> StravaTokenResponse:
        return self._request_token(
            {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
                "grant_type": "authorization_code",
            }
        )

    def refresh_token(self, refresh_token: str) -> StravaTokenResponse:
        return self._request_token(
            {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        )

    def get_athlete(self, access_token: str) -> StravaAthlete:
        try:
            response = httpx.get(
                STRAVA_ATHLETE_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
        except httpx.HTTPError as exc:
            raise StravaAuthError("Strava API request failed") from exc

        if response.status_code >= 500:
            raise StravaAuthError(f"Strava API unavailable: {response.status_code}")
        if response.status_code >= 400:
            raise StravaAuthError(f"Strava athlete request failed: {response.status_code}")

        data = response.json()
        return StravaAthlete(id=int(data["id"]))

    def _request_token(self, payload: dict[str, str]) -> StravaTokenResponse:
        try:
            response = httpx.post(STRAVA_OAUTH_URL, data=payload, timeout=30.0)
        except httpx.HTTPError as exc:
            raise StravaAuthError("Strava API request failed") from exc

        if response.status_code >= 500:
            raise StravaAuthError(f"Strava API unavailable: {response.status_code}")
        if response.status_code >= 400:
            raise StravaAuthError(f"Strava token request failed: {response.status_code}")

        data = response.json()
        athlete = data.get("athlete")
        athlete_id = int(athlete["id"]) if athlete is not None else int(data["athlete_id"])
        return StravaTokenResponse(
            access_token=str(data["access_token"]),
            refresh_token=str(data["refresh_token"]),
            expires_at=expires_at_from_unix(int(data["expires_at"])),
            athlete_id=athlete_id,
        )

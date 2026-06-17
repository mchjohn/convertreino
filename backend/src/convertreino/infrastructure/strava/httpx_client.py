from typing import Any

import httpx

from convertreino.domain.exceptions import (
    StravaActivityNotFoundError,
    StravaApiError,
    StravaAuthError,
)
from convertreino.infrastructure.strava.client import (
    StravaActivitySummary,
    StravaAthlete,
    StravaTokenResponse,
    expires_at_from_unix,
)

STRAVA_OAUTH_URL = "https://www.strava.com/oauth/token"
STRAVA_ATHLETE_URL = "https://www.strava.com/api/v3/athlete"
STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
STRAVA_ACTIVITY_URL = "https://www.strava.com/api/v3/activities"


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

    def list_activities(
        self,
        access_token: str,
        *,
        page: int = 1,
        per_page: int = 200,
    ) -> list[StravaActivitySummary]:
        try:
            response = httpx.get(
                STRAVA_ACTIVITIES_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"page": page, "per_page": per_page},
                timeout=30.0,
            )
        except httpx.HTTPError as exc:
            raise StravaApiError("Strava API request failed") from exc

        if response.status_code in {401, 403}:
            raise StravaAuthError("Reauthorize Strava account")
        if response.status_code >= 500:
            raise StravaApiError(f"Strava API unavailable: {response.status_code}")
        if response.status_code >= 400:
            raise StravaAuthError(f"Strava activities request failed: {response.status_code}")

        return [_parse_activity_summary(item) for item in response.json()]

    def get_activity(self, access_token: str, activity_id: int) -> StravaActivitySummary:
        try:
            response = httpx.get(
                f"{STRAVA_ACTIVITY_URL}/{activity_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
        except httpx.HTTPError as exc:
            raise StravaApiError("Strava API request failed") from exc

        if response.status_code in {401, 403}:
            raise StravaAuthError("Reauthorize Strava account")
        if response.status_code == 404:
            raise StravaActivityNotFoundError(f"Strava activity not found: {activity_id}")
        if response.status_code >= 500:
            raise StravaApiError(f"Strava API unavailable: {response.status_code}")
        if response.status_code >= 400:
            raise StravaAuthError(f"Strava activity request failed: {response.status_code}")

        return _parse_activity_summary(response.json())

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


def _parse_activity_summary(data: dict[str, Any]) -> StravaActivitySummary:
    elapsed = data.get("elapsed_time")
    moving = data.get("moving_time")
    distance = data.get("distance")
    return StravaActivitySummary(
        id=int(data["id"]),
        start_date=str(data["start_date"]),
        type=str(data["type"]),
        distance=float(distance) if distance is not None else 0.0,
        elapsed_time=int(elapsed) if elapsed is not None else None,
        moving_time=int(moving) if moving is not None else None,
    )

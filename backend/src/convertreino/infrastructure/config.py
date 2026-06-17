import os
from dataclasses import dataclass
from urllib.parse import urlencode


@dataclass(frozen=True, slots=True)
class StravaSettings:
    client_id: str
    client_secret: str
    redirect_uri: str


def get_strava_settings() -> StravaSettings:
    client_id = os.environ.get("STRAVA_CLIENT_ID", "")
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("STRAVA_REDIRECT_URI", "")
    return StravaSettings(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )


STRAVA_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
STRAVA_DEFAULT_SCOPE = "read,activity:read_all"


def build_authorization_url(*, client_id: str, redirect_uri: str, scope: str = STRAVA_DEFAULT_SCOPE) -> str:
    params = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "approval_prompt": "auto",
        }
    )
    return f"{STRAVA_AUTHORIZE_URL}?{params}"

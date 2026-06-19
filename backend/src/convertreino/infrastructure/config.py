import convertreino.infrastructure.load_env  # noqa: F401

import os
import sys
from dataclasses import dataclass
from urllib.parse import urlencode

from convertreino.application.jwt_token_service import JwtSettings


@dataclass(frozen=True, slots=True)
class StravaSettings:
    client_id: str
    client_secret: str
    redirect_uri: str
    mobile_redirect_uri: str


@dataclass(frozen=True, slots=True)
class StravaWebhookSettings:
    verify_token: str
    callback_url: str


def get_strava_webhook_settings() -> StravaWebhookSettings:
    return StravaWebhookSettings(
        verify_token=os.environ.get("STRAVA_WEBHOOK_VERIFY_TOKEN", ""),
        callback_url=os.environ.get("STRAVA_WEBHOOK_CALLBACK_URL", ""),
    )


def get_strava_settings() -> StravaSettings:
    client_id = os.environ.get("STRAVA_CLIENT_ID", "")
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("STRAVA_REDIRECT_URI", "")
    mobile_redirect_uri = os.environ.get("STRAVA_MOBILE_REDIRECT_URI", redirect_uri)
    return StravaSettings(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        mobile_redirect_uri=mobile_redirect_uri,
    )


STRAVA_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
STRAVA_DEFAULT_SCOPE = "read,activity:read_all"


def _is_test_runtime() -> bool:
    return "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST") is not None


def get_jwt_settings() -> JwtSettings:
    secret = os.environ.get("JWT_SECRET", "")
    if not secret and _is_test_runtime():
        secret = "test-jwt-secret"
    expires_raw = os.environ.get("JWT_EXPIRES_MINUTES", "60")
    return JwtSettings(secret=secret, expires_minutes=int(expires_raw))


@dataclass(frozen=True, slots=True)
class ChatSettings:
    openai_api_key: str
    openai_model: str
    max_tool_iterations: int


def get_chat_settings() -> ChatSettings:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key and _is_test_runtime():
        api_key = "test-openai-key"
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    max_iterations_raw = os.environ.get("CHAT_MAX_TOOL_ITERATIONS", "5")
    return ChatSettings(
        openai_api_key=api_key,
        openai_model=model,
        max_tool_iterations=int(max_iterations_raw),
    )


def build_authorization_url(
    *,
    client_id: str,
    redirect_uri: str,
    scope: str = STRAVA_DEFAULT_SCOPE,
) -> str:
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

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
    llm_provider: str
    openai_api_key: str
    openai_model: str
    groq_api_key: str
    groq_model: str
    max_tool_iterations: int


def get_chat_settings() -> ChatSettings:
    llm_provider = os.environ.get("LLM_PROVIDER", "openai").strip().lower()
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_api_key and _is_test_runtime():
        openai_api_key = "test-openai-key"
    groq_api_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_api_key and _is_test_runtime():
        groq_api_key = "test-groq-key"
    openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    max_iterations_raw = os.environ.get("CHAT_MAX_TOOL_ITERATIONS", "5")
    return ChatSettings(
        llm_provider=llm_provider,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        groq_api_key=groq_api_key,
        groq_model=groq_model,
        max_tool_iterations=int(max_iterations_raw),
    )


@dataclass(frozen=True, slots=True)
class PhoenixSettings:
    enabled: bool
    collector_endpoint: str
    project_name: str


def _parse_bool_env(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def get_phoenix_settings() -> PhoenixSettings:
    enabled = _parse_bool_env("PHOENIX_ENABLED", default=False)
    if _is_test_runtime():
        enabled = False
    return PhoenixSettings(
        enabled=enabled,
        collector_endpoint=os.environ.get(
            "PHOENIX_COLLECTOR_ENDPOINT",
            "http://localhost:6006/v1/traces",
        ),
        project_name=os.environ.get("PHOENIX_PROJECT_NAME", "convertreino-dev"),
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

from collections.abc import Callable, Generator
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from convertreino.application.jwt_token_service import JwtTokenService
from convertreino.application.strava_oauth_service import StravaOAuthService
from convertreino.application.strava_sync_service import StravaSyncService
from convertreino.application.strava_webhook_processor import StravaWebhookProcessor
from convertreino.domain.exceptions import InvalidTokenError
from convertreino.domain.repositories.activity_repository import ActivityRepository
from convertreino.domain.repositories.user_repository import UserRepository
from convertreino.infrastructure.config import (
    StravaWebhookSettings,
    get_jwt_settings,
    get_strava_settings,
    get_strava_webhook_settings,
)
from convertreino.infrastructure.db.session import create_session_factory
from convertreino.infrastructure.repositories.sqlalchemy_activity_repository import (
    SqlAlchemyActivityRepository,
)
from convertreino.infrastructure.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from convertreino.infrastructure.strava.fake_client import FakeStravaApiClient
from convertreino.infrastructure.strava.httpx_client import HttpxStravaApiClient

_oauth_service_override: StravaOAuthService | None = None
_sync_service_override: StravaSyncService | None = None
_webhook_processor_override: StravaWebhookProcessor | None = None
_webhook_settings_override: StravaWebhookSettings | None = None
_jwt_service_override: JwtTokenService | None = None

security = HTTPBearer(auto_error=False)


def set_oauth_service_override(service: StravaOAuthService | None) -> None:
    global _oauth_service_override
    _oauth_service_override = service


def set_sync_service_override(service: StravaSyncService | None) -> None:
    global _sync_service_override
    _sync_service_override = service


def set_webhook_processor_override(processor: StravaWebhookProcessor | None) -> None:
    global _webhook_processor_override
    _webhook_processor_override = processor


def set_webhook_settings_override(settings: StravaWebhookSettings | None) -> None:
    global _webhook_settings_override
    _webhook_settings_override = settings


def set_jwt_service_override(service: JwtTokenService | None) -> None:
    global _jwt_service_override
    _jwt_service_override = service


def get_jwt_token_service() -> JwtTokenService:
    if _jwt_service_override is not None:
        return _jwt_service_override
    return JwtTokenService(get_jwt_settings())


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),  # noqa: B008
    jwt_service: JwtTokenService = Depends(get_jwt_token_service),  # noqa: B008
) -> UUID:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return jwt_service.decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def _build_oauth_service(session: Session) -> StravaOAuthService:
    settings = get_strava_settings()
    user_repo = SqlAlchemyUserRepository(session)
    strava_client = HttpxStravaApiClient(
        client_id=settings.client_id,
        client_secret=settings.client_secret,
    )
    return StravaOAuthService(
        user_repo=user_repo,
        strava_client=strava_client,
        client_id=settings.client_id,
        redirect_uri=settings.redirect_uri,
    )


def _build_sync_service(session: Session) -> StravaSyncService:
    oauth_service = _build_oauth_service(session)
    user_repo = SqlAlchemyUserRepository(session)
    activity_repo = SqlAlchemyActivityRepository(session)
    settings = get_strava_settings()
    strava_client = HttpxStravaApiClient(
        client_id=settings.client_id,
        client_secret=settings.client_secret,
    )
    return StravaSyncService(
        user_repo=user_repo,
        activity_repo=activity_repo,
        strava_client=strava_client,
        oauth_service=oauth_service,
        page_commit=session.commit,
    )


def get_db_session() -> Generator[Session, None, None]:
    session_factory = create_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_strava_oauth_service(
    session: Session = Depends(get_db_session),  # noqa: B008
) -> StravaOAuthService:
    if _oauth_service_override is not None:
        return _oauth_service_override
    return _build_oauth_service(session)


def get_strava_sync_service(
    session: Session = Depends(get_db_session),  # noqa: B008
) -> StravaSyncService:
    if _sync_service_override is not None:
        return _sync_service_override
    return _build_sync_service(session)


def _build_webhook_processor(session: Session) -> StravaWebhookProcessor:
    oauth_service = _build_oauth_service(session)
    user_repo = SqlAlchemyUserRepository(session)
    activity_repo = SqlAlchemyActivityRepository(session)
    settings = get_strava_settings()
    strava_client = HttpxStravaApiClient(
        client_id=settings.client_id,
        client_secret=settings.client_secret,
    )
    return StravaWebhookProcessor(
        user_repo=user_repo,
        activity_repo=activity_repo,
        strava_client=strava_client,
        oauth_service=oauth_service,
    )


def get_strava_webhook_processor(
    session: Session = Depends(get_db_session),  # noqa: B008
) -> StravaWebhookProcessor:
    if _webhook_processor_override is not None:
        return _webhook_processor_override
    return _build_webhook_processor(session)


def get_strava_webhook_settings_dep() -> StravaWebhookSettings:
    if _webhook_settings_override is not None:
        return _webhook_settings_override
    return get_strava_webhook_settings()


def build_test_oauth_service(
    *,
    user_repo: UserRepository,
    strava_client: FakeStravaApiClient | None = None,
    client_id: str = "fake-client-id",
    redirect_uri: str = "http://localhost:8000/auth/strava/callback",
) -> StravaOAuthService:
    return StravaOAuthService(
        user_repo=user_repo,
        strava_client=strava_client or FakeStravaApiClient(),
        client_id=client_id,
        redirect_uri=redirect_uri,
    )


def build_test_sync_service(
    *,
    user_repo: UserRepository,
    activity_repo: ActivityRepository,
    strava_client: FakeStravaApiClient | None = None,
    client_id: str = "fake-client-id",
    redirect_uri: str = "http://localhost:8000/auth/strava/callback",
    page_commit: Callable[[], None] | None = None,
) -> StravaSyncService:
    client = strava_client or FakeStravaApiClient()
    oauth_service = StravaOAuthService(
        user_repo=user_repo,
        strava_client=client,
        client_id=client_id,
        redirect_uri=redirect_uri,
    )
    return StravaSyncService(
        user_repo=user_repo,
        activity_repo=activity_repo,
        strava_client=client,
        oauth_service=oauth_service,
        page_commit=page_commit,
    )


def build_test_webhook_processor(
    *,
    user_repo: UserRepository,
    activity_repo: ActivityRepository,
    strava_client: FakeStravaApiClient | None = None,
    client_id: str = "fake-client-id",
    redirect_uri: str = "http://localhost:8000/auth/strava/callback",
) -> StravaWebhookProcessor:
    client = strava_client or FakeStravaApiClient()
    oauth_service = StravaOAuthService(
        user_repo=user_repo,
        strava_client=client,
        client_id=client_id,
        redirect_uri=redirect_uri,
    )
    return StravaWebhookProcessor(
        user_repo=user_repo,
        activity_repo=activity_repo,
        strava_client=client,
        oauth_service=oauth_service,
    )

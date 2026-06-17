from collections.abc import Callable, Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from convertreino.application.strava_oauth_service import StravaOAuthService
from convertreino.application.strava_sync_service import StravaSyncService
from convertreino.domain.repositories.activity_repository import ActivityRepository
from convertreino.domain.repositories.user_repository import UserRepository
from convertreino.infrastructure.config import get_strava_settings
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


def set_oauth_service_override(service: StravaOAuthService | None) -> None:
    global _oauth_service_override
    _oauth_service_override = service


def set_sync_service_override(service: StravaSyncService | None) -> None:
    global _sync_service_override
    _sync_service_override = service


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
    session: Session = Depends(get_db_session),
) -> StravaOAuthService:
    if _oauth_service_override is not None:
        return _oauth_service_override
    return _build_oauth_service(session)


def get_strava_sync_service(
    session: Session = Depends(get_db_session),
) -> StravaSyncService:
    if _sync_service_override is not None:
        return _sync_service_override
    return _build_sync_service(session)


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

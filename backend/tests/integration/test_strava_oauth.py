import os
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from convertreino.api.dependencies import (
    build_test_oauth_service,
    set_oauth_service_override,
)
from convertreino.api.main import create_app
from convertreino.domain.exceptions import DomainIntegrityError
from convertreino.infrastructure.db.models import Base, UserModel
from convertreino.infrastructure.repositories.in_memory_user_repository import (
    InMemoryUserRepository,
)
from convertreino.infrastructure.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from convertreino.infrastructure.strava.fake_client import FakeStravaApiClient
from tests.builders import build_user

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://convertreino:convertreino@localhost:5432/convertreino_test",
)

pytestmark = pytest.mark.integration


def _postgres_available() -> bool:
    try:
        engine = create_engine(TEST_DATABASE_URL)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
def reset_oauth_override():
    set_oauth_service_override(None)
    yield
    set_oauth_service_override(None)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    if not _postgres_available():
        pytest.skip("PostgreSQL not available for integration tests")

    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    fake_strava = FakeStravaApiClient(athlete_id=77_777)
    user_repo = SqlAlchemyUserRepository(db_session)
    service = build_test_oauth_service(user_repo=user_repo, strava_client=fake_strava)
    set_oauth_service_override(service)
    return TestClient(create_app())


def test_authorize_returns_strava_url_with_required_params(client: TestClient):
    # Arrange — CN-3 integration

    # Act
    response = client.get("/auth/strava/authorize")

    # Assert
    assert response.status_code == 200
    url = response.json()["authorization_url"]
    assert "client_id=fake-client-id" in url
    assert "redirect_uri=" in url
    assert "response_type=code" in url
    assert "scope=read" in url


def test_callback_creates_user_and_returns_user_id(client: TestClient, db_session: Session):
    # Arrange — CN-1 integration

    # Act
    response = client.get("/auth/strava/callback", params={"code": "oauth-code"})

    # Assert
    assert response.status_code == 200
    user_id = UUID(response.json()["user_id"])
    repo = SqlAlchemyUserRepository(db_session)
    user = repo.get_by_id(user_id)
    assert user is not None
    assert user.strava_athlete_id == 77_777
    assert user.access_token is not None


def test_callback_updates_existing_user_on_re_oauth(client: TestClient, db_session: Session):
    # Arrange — CN-2 integration
    first = client.get("/auth/strava/callback", params={"code": "first-code"})
    user_id = first.json()["user_id"]

    # Act
    second = client.get("/auth/strava/callback", params={"code": "second-code"})

    # Assert
    assert second.status_code == 200
    assert second.json()["user_id"] == user_id
    repo = SqlAlchemyUserRepository(db_session)
    user = repo.get_by_strava_athlete_id(77_777)
    assert user is not None
    assert str(user.id) == user_id


def test_callback_returns_400_on_invalid_code(db_session: Session):
    # Arrange — CE-1 integration
    fake_strava = FakeStravaApiClient(fail_exchange=True)
    user_repo = SqlAlchemyUserRepository(db_session)
    set_oauth_service_override(
        build_test_oauth_service(user_repo=user_repo, strava_client=fake_strava)
    )
    client = TestClient(create_app())

    # Act
    response = client.get("/auth/strava/callback", params={"code": "bad-code"})

    # Assert
    assert response.status_code == 400
    assert _user_count(db_session) == 0


def test_in_memory_repo_raises_on_duplicate_strava_athlete_id():
    # Arrange — CE-4
    athlete_id = 12_345
    repo = InMemoryUserRepository()
    repo.save(
        build_user(
            strava_athlete_id=athlete_id,
            access_token="a",
            refresh_token="r",
            token_expires_at=datetime.now(UTC),
        )
    )
    duplicate = build_user(
        strava_athlete_id=athlete_id,
        access_token="b",
        refresh_token="s",
        token_expires_at=datetime.now(UTC),
    )

    # Act / Assert
    with pytest.raises(DomainIntegrityError):
        repo.save(duplicate)


def _user_count(session: Session) -> int:
    return len(session.scalars(select(UserModel)).all())

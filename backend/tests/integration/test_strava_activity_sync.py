import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from convertreino.api.dependencies import build_test_sync_service, set_sync_service_override
from convertreino.api.main import create_app
from convertreino.domain.exceptions import DomainIntegrityError
from convertreino.infrastructure.db.models import Base
from convertreino.infrastructure.repositories.sqlalchemy_activity_repository import (
    SqlAlchemyActivityRepository,
)
from convertreino.infrastructure.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from convertreino.infrastructure.strava.fake_client import FakeStravaApiClient
from tests.builders import build_activity, build_strava_activity_summary, build_user

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


def _create_unique_external_id_index(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_activities_user_external_id "
                "ON activities (user_id, external_id) "
                "WHERE external_id IS NOT NULL"
            )
        )


@pytest.fixture(autouse=True)
def reset_sync_override():
    set_sync_service_override(None)
    yield
    set_sync_service_override(None)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    if not _postgres_available():
        pytest.skip("PostgreSQL not available for integration tests")

    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    _create_unique_external_id_index(engine)
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


def _save_linked_user(db_session: Session):
    user = build_user(
        strava_athlete_id=88_888,
        access_token="access",
        refresh_token="refresh",
        token_expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    SqlAlchemyUserRepository(db_session).save(user)
    db_session.commit()
    return user


def test_upsert_creates_then_updates_without_duplicates(db_session: Session):
    # Arrange — migration 003 + upsert contract
    user = _save_linked_user(db_session)
    repo = SqlAlchemyActivityRepository(db_session)
    activity = build_activity(user_id=user.id, external_id="9001", distance_meters=1000.0)

    # Act
    created = repo.upsert(activity)
    db_session.commit()
    updated_input = build_activity(
        id=uuid4(),
        user_id=user.id,
        external_id="9001",
        distance_meters=2000.0,
    )
    updated = repo.upsert(updated_input)
    db_session.commit()

    # Assert
    assert created.external_id == "9001"
    assert updated.id == created.id
    assert updated.distance_meters == 2000.0
    assert len(repo.get_all(user.id)) == 1


def test_sync_endpoint_returns_counts(db_session: Session):
    # Arrange — CN-4
    user = _save_linked_user(db_session)
    activities = [
        build_strava_activity_summary(id=1001),
        build_strava_activity_summary(id=1002),
    ]
    fake_strava = FakeStravaApiClient(activities=activities)
    user_repo = SqlAlchemyUserRepository(db_session)
    activity_repo = SqlAlchemyActivityRepository(db_session)
    service = build_test_sync_service(
        user_repo=user_repo,
        activity_repo=activity_repo,
        strava_client=fake_strava,
        page_commit=db_session.commit,
    )
    set_sync_service_override(service)
    client = TestClient(create_app())

    # Act
    response = client.post(f"/users/{user.id}/sync/strava")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["created_count"] == 2
    assert body["synced_count"] == 2
    assert body["updated_count"] == 0
    assert body["skipped_count"] == 0


def test_sync_endpoint_returns_404_for_unknown_user(db_session: Session):
    # Arrange — CE-1 integration
    user_repo = SqlAlchemyUserRepository(db_session)
    activity_repo = SqlAlchemyActivityRepository(db_session)
    service = build_test_sync_service(
        user_repo=user_repo,
        activity_repo=activity_repo,
        strava_client=FakeStravaApiClient(),
    )
    set_sync_service_override(service)
    client = TestClient(create_app())
    unknown_id = uuid4()

    # Act
    response = client.post(f"/users/{unknown_id}/sync/strava")

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_sync_endpoint_returns_502_on_strava_server_error(db_session: Session):
    # Arrange — CE-4 integration
    user = _save_linked_user(db_session)
    fake_strava = FakeStravaApiClient(
        activities=[build_strava_activity_summary(id=2001)],
        fail_list_server_pages={1},
    )
    user_repo = SqlAlchemyUserRepository(db_session)
    activity_repo = SqlAlchemyActivityRepository(db_session)
    service = build_test_sync_service(
        user_repo=user_repo,
        activity_repo=activity_repo,
        strava_client=fake_strava,
        page_commit=db_session.commit,
    )
    set_sync_service_override(service)
    client = TestClient(create_app())

    # Act
    response = client.post(f"/users/{user.id}/sync/strava")

    # Assert
    assert response.status_code == 502
    assert response.json()["detail"] == "Strava API unavailable"
    assert len(activity_repo.get_all(user.id)) == 0


def test_unique_index_prevents_duplicate_external_id(db_session: Session):
    # Arrange — CE-5 / migration 003
    user = _save_linked_user(db_session)
    repo = SqlAlchemyActivityRepository(db_session)
    first = build_activity(user_id=user.id, external_id="dup-1")
    second = build_activity(user_id=user.id, external_id="dup-1")
    repo.save(first)
    db_session.commit()

    # Act / Assert
    with pytest.raises(DomainIntegrityError):
        repo.save(second)
        db_session.flush()


def test_synced_activities_have_external_id(db_session: Session):
    # Arrange
    user = _save_linked_user(db_session)
    fake_strava = FakeStravaApiClient(
        activities=[build_strava_activity_summary(id=3001, distance=1234.0)]
    )
    activity_repo = SqlAlchemyActivityRepository(db_session)
    service = build_test_sync_service(
        user_repo=SqlAlchemyUserRepository(db_session),
        activity_repo=activity_repo,
        strava_client=fake_strava,
        page_commit=db_session.commit,
    )

    # Act
    result = service.sync_user(user.id)
    db_session.commit()

    # Assert
    assert result.created_count == 1
    activities = activity_repo.get_all(user.id)
    assert len(activities) == 1
    assert activities[0].external_id == "3001"
    assert activities[0].distance_meters == 1234.0

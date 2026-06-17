import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from convertreino.api.dependencies import (
    build_test_webhook_processor,
    set_webhook_processor_override,
    set_webhook_settings_override,
)
from convertreino.api.main import create_app
from convertreino.infrastructure.config import StravaWebhookSettings
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

VERIFY_TOKEN = "test-verify-token"
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
def reset_webhook_overrides():
    set_webhook_processor_override(None)
    set_webhook_settings_override(None)
    yield
    set_webhook_processor_override(None)
    set_webhook_settings_override(None)


@pytest.fixture
def webhook_settings() -> StravaWebhookSettings:
    return StravaWebhookSettings(
        verify_token=VERIFY_TOKEN,
        callback_url="https://example.com/webhooks/strava",
    )


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


def _save_linked_user(db_session: Session, *, athlete_id: int = 88_888):
    user = build_user(
        strava_athlete_id=athlete_id,
        access_token="access",
        refresh_token="refresh",
        token_expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    SqlAlchemyUserRepository(db_session).save(user)
    db_session.commit()
    return user


def _client_with_processor(
    db_session: Session,
    fake_strava: FakeStravaApiClient,
    webhook_settings: StravaWebhookSettings,
) -> TestClient:
    user_repo = SqlAlchemyUserRepository(db_session)
    activity_repo = SqlAlchemyActivityRepository(db_session)
    processor = build_test_webhook_processor(
        user_repo=user_repo,
        activity_repo=activity_repo,
        strava_client=fake_strava,
    )
    set_webhook_processor_override(processor)
    set_webhook_settings_override(webhook_settings)
    return TestClient(create_app())


def test_get_challenge_returns_hub_challenge(webhook_settings: StravaWebhookSettings):
    # Arrange — CN-1
    set_webhook_settings_override(webhook_settings)
    client = TestClient(create_app())

    # Act
    response = client.get(
        "/webhooks/strava",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "abc123",
            "hub.verify_token": VERIFY_TOKEN,
        },
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {"hub.challenge": "abc123"}


def test_get_challenge_returns_403_for_invalid_token(webhook_settings: StravaWebhookSettings):
    # Arrange — CE-1
    set_webhook_settings_override(webhook_settings)
    client = TestClient(create_app())

    # Act
    response = client.get(
        "/webhooks/strava",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "abc123",
            "hub.verify_token": "wrong-token",
        },
    )

    # Assert
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid verify token"


def test_post_activity_create_persists_activity(
    db_session: Session,
    webhook_settings: StravaWebhookSettings,
):
    # Arrange — CN-2 integration
    user = _save_linked_user(db_session, athlete_id=88_001)
    summary = build_strava_activity_summary(id=9001, distance=12345.0)
    fake_strava = FakeStravaApiClient(activities=[summary])
    client = _client_with_processor(db_session, fake_strava, webhook_settings)
    activity_repo = SqlAlchemyActivityRepository(db_session)
    payload = {
        "object_type": "activity",
        "aspect_type": "create",
        "object_id": 9001,
        "owner_id": 88_001,
        "event_time": 1_700_000_000,
        "subscription_id": 1,
        "updates": {},
    }

    # Act
    response = client.post("/webhooks/strava", json=payload)
    db_session.commit()

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "created"
    assert body["user_id"] == str(user.id)
    activities = activity_repo.get_all(user.id)
    assert len(activities) == 1
    assert activities[0].external_id == "9001"
    assert activities[0].distance_meters == 12345.0


def test_post_invalid_payload_returns_400(webhook_settings: StravaWebhookSettings):
    # Arrange — CE-2
    set_webhook_settings_override(webhook_settings)
    client = TestClient(create_app())

    # Act
    response = client.post("/webhooks/strava", json={"object_type": "activity"})

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid webhook payload"


def test_delete_by_external_id_removes_activity(db_session: Session):
    # Arrange
    user = _save_linked_user(db_session)
    repo = SqlAlchemyActivityRepository(db_session)
    repo.save(build_activity(user_id=user.id, external_id="del-pg-1"))
    db_session.commit()

    # Act
    deleted = repo.delete_by_external_id(user.id, "del-pg-1")
    missing = repo.delete_by_external_id(user.id, "del-pg-1")
    db_session.commit()

    # Assert
    assert deleted is True
    assert missing is False
    assert len(repo.get_all(user.id)) == 0


def test_post_activity_delete_removes_local_activity(
    db_session: Session,
    webhook_settings: StravaWebhookSettings,
):
    # Arrange — CN-4 integration
    user = _save_linked_user(db_session, athlete_id=88_002)
    activity_repo = SqlAlchemyActivityRepository(db_session)
    activity_repo.save(build_activity(user_id=user.id, external_id="9002"))
    db_session.commit()
    client = _client_with_processor(db_session, FakeStravaApiClient(), webhook_settings)
    payload = {
        "object_type": "activity",
        "aspect_type": "delete",
        "object_id": 9002,
        "owner_id": 88_002,
        "event_time": 1_700_000_000,
        "subscription_id": 1,
        "updates": {},
    }

    # Act
    response = client.post("/webhooks/strava", json=payload)
    db_session.commit()

    # Assert
    assert response.status_code == 200
    assert response.json()["action"] == "deleted"
    assert activity_repo.get_by_external_id(user.id, "9002") is None

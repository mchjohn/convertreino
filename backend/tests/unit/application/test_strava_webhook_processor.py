from datetime import UTC, datetime, timedelta
from uuid import uuid4

from convertreino.application.strava_webhook_processor import StravaWebhookProcessor
from convertreino.infrastructure.repositories.in_memory_activity_repository import (
    InMemoryActivityRepository,
)
from convertreino.infrastructure.repositories.in_memory_user_repository import (
    InMemoryUserRepository,
)
from convertreino.infrastructure.strava.fake_client import FakeStravaApiClient
from tests.builders import (
    build_activity,
    build_strava_activity_summary,
    build_strava_webhook_event,
    build_user,
)

CLIENT_ID = "test-client-id"
REDIRECT_URI = "http://localhost:8000/auth/strava/callback"
ATHLETE_ID = 88_001


def _linked_user(**kwargs: object):
    defaults = {
        "strava_athlete_id": ATHLETE_ID,
        "access_token": "valid-access",
        "refresh_token": "valid-refresh",
        "token_expires_at": datetime.now(UTC) + timedelta(hours=1),
    }
    defaults.update(kwargs)
    return build_user(**defaults)  # type: ignore[arg-type]


def _processor(
    user_repo: InMemoryUserRepository,
    activity_repo: InMemoryActivityRepository,
    client: FakeStravaApiClient,
) -> StravaWebhookProcessor:
    from convertreino.application.strava_oauth_service import StravaOAuthService

    oauth = StravaOAuthService(
        user_repo=user_repo,
        strava_client=client,
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
    )
    return StravaWebhookProcessor(
        user_repo=user_repo,
        activity_repo=activity_repo,
        strava_client=client,
        oauth_service=oauth,
    )


def test_activity_create_persists_new_activity():
    # Arrange — CN-2
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    summary = build_strava_activity_summary(id=5001, distance=8000.0)
    client = FakeStravaApiClient(activities=[summary])
    processor = _processor(user_repo, activity_repo, client)
    event = build_strava_webhook_event(
        object_type="activity",
        aspect_type="create",
        object_id=5001,
        owner_id=ATHLETE_ID,
    )

    # Act
    result = processor.handle_event(event)

    # Assert
    assert result.action == "created"
    assert result.user_id == user.id
    stored = activity_repo.get_all(user.id)
    assert len(stored) == 1
    assert stored[0].external_id == "5001"
    assert stored[0].distance_meters == 8000.0


def test_activity_update_updates_existing_activity():
    # Arrange — CN-3
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    existing = build_activity(user_id=user.id, external_id="5002", distance_meters=1000.0)
    activity_repo.save(existing)
    summary = build_strava_activity_summary(id=5002, distance=9000.0)
    client = FakeStravaApiClient(activities=[summary])
    processor = _processor(user_repo, activity_repo, client)
    event = build_strava_webhook_event(
        object_type="activity",
        aspect_type="update",
        object_id=5002,
        owner_id=ATHLETE_ID,
    )

    # Act
    result = processor.handle_event(event)

    # Assert
    assert result.action == "updated"
    stored = activity_repo.get_by_external_id(user.id, "5002")
    assert stored is not None
    assert stored.id == existing.id
    assert stored.distance_meters == 9000.0


def test_activity_delete_removes_local_activity():
    # Arrange — CN-4
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    activity_repo.save(build_activity(user_id=user.id, external_id="5003"))
    client = FakeStravaApiClient()
    processor = _processor(user_repo, activity_repo, client)
    event = build_strava_webhook_event(
        object_type="activity",
        aspect_type="delete",
        object_id=5003,
        owner_id=ATHLETE_ID,
    )

    # Act
    result = processor.handle_event(event)

    # Assert
    assert result.action == "deleted"
    assert activity_repo.get_by_external_id(user.id, "5003") is None


def test_athlete_deauth_clears_tokens():
    # Arrange — CN-5
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    activity_repo.save(build_activity(user_id=user.id, external_id="keep-me"))
    client = FakeStravaApiClient()
    processor = _processor(user_repo, activity_repo, client)
    event = build_strava_webhook_event(
        object_type="athlete",
        aspect_type="update",
        object_id=ATHLETE_ID,
        owner_id=ATHLETE_ID,
        updates={"authorized": "false"},
    )

    # Act
    result = processor.handle_event(event)

    # Assert
    assert result.action == "deauthorized"
    updated = user_repo.get_by_id(user.id)
    assert updated is not None
    assert updated.access_token is None
    assert updated.refresh_token is None
    assert updated.token_expires_at is None
    assert updated.strava_athlete_id == ATHLETE_ID
    assert len(activity_repo.get_all(user.id)) == 1


def test_delete_missing_activity_is_idempotent():
    # Arrange — CB-1
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    processor = _processor(user_repo, activity_repo, FakeStravaApiClient())
    event = build_strava_webhook_event(
        object_type="activity",
        aspect_type="delete",
        object_id=9999,
        owner_id=ATHLETE_ID,
    )

    # Act
    result = processor.handle_event(event)

    # Assert
    assert result.action == "deleted"
    assert len(activity_repo.get_all(user.id)) == 0


def test_unknown_athlete_is_ignored():
    # Arrange — CB-2
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    processor = _processor(user_repo, activity_repo, FakeStravaApiClient())
    event = build_strava_webhook_event(owner_id=77_777)

    # Act
    result = processor.handle_event(event)

    # Assert
    assert result.action == "ignored"
    assert result.user_id is None


def test_invalid_activity_from_mapper_is_ignored():
    # Arrange — CB-3
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    summary = build_strava_activity_summary(id=5100, distance=-1.0)
    client = FakeStravaApiClient(activities=[summary])
    processor = _processor(user_repo, activity_repo, client)
    event = build_strava_webhook_event(object_id=5100, owner_id=ATHLETE_ID)

    # Act
    result = processor.handle_event(event)

    # Assert
    assert result.action == "ignored"
    assert len(activity_repo.get_all(user.id)) == 0


def test_near_expiry_token_is_refreshed_before_fetch():
    # Arrange — CB-4
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user(token_expires_at=datetime.now(UTC) + timedelta(minutes=1))
    user_repo.save(user)
    summary = build_strava_activity_summary(id=5200)
    client = FakeStravaApiClient(access_token="valid-access", activities=[summary])
    processor = _processor(user_repo, activity_repo, client)
    event = build_strava_webhook_event(object_id=5200, owner_id=ATHLETE_ID)

    # Act
    processor.handle_event(event)

    # Assert
    assert len(client.refresh_calls) == 1
    updated = user_repo.get_by_id(user.id)
    assert updated is not None
    assert updated.access_token == "valid-access-refreshed"


def test_duplicate_create_event_becomes_update():
    # Arrange — CB-5
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    summary = build_strava_activity_summary(id=6001)
    client = FakeStravaApiClient(activities=[summary])
    processor = _processor(user_repo, activity_repo, client)
    event = build_strava_webhook_event(object_id=6001, owner_id=ATHLETE_ID)
    processor.handle_event(event)

    # Act
    result = processor.handle_event(event)

    # Assert
    assert result.action == "updated"
    assert len(activity_repo.get_all(user.id)) == 1


def test_get_activity_auth_error_is_ignored():
    # Arrange — CE-3
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    client = FakeStravaApiClient(fail_get_auth_ids={6100})
    processor = _processor(user_repo, activity_repo, client)
    event = build_strava_webhook_event(object_id=6100, owner_id=ATHLETE_ID)

    # Act
    result = processor.handle_event(event)

    # Assert
    assert result.action == "ignored"
    assert len(activity_repo.get_all(user.id)) == 0


def test_get_activity_not_found_deletes_existing_local_activity():
    # Arrange — CE-4 with local record
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    activity_repo.save(build_activity(user_id=user.id, external_id="7001"))
    client = FakeStravaApiClient(fail_get_not_found_ids={7001})
    processor = _processor(user_repo, activity_repo, client)
    event = build_strava_webhook_event(object_id=7001, owner_id=ATHLETE_ID)

    # Act
    result = processor.handle_event(event)

    # Assert
    assert result.action == "deleted"
    assert activity_repo.get_by_external_id(user.id, "7001") is None


def test_get_activity_not_found_without_local_record_is_ignored():
    # Arrange — CE-4 without local record
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    client = FakeStravaApiClient(fail_get_not_found_ids={7002})
    processor = _processor(user_repo, activity_repo, client)
    event = build_strava_webhook_event(object_id=7002, owner_id=ATHLETE_ID)

    # Act
    result = processor.handle_event(event)

    # Assert
    assert result.action == "ignored"


def test_delete_by_external_id_in_memory_repository():
    # Arrange
    user_id = uuid4()
    repo = InMemoryActivityRepository(
        [build_activity(user_id=user_id, external_id="del-1")]
    )

    # Act
    deleted = repo.delete_by_external_id(user_id, "del-1")
    missing = repo.delete_by_external_id(user_id, "del-1")

    # Assert
    assert deleted is True
    assert missing is False
    assert repo.get_all(user_id) == []

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from convertreino.application.strava_sync_service import StravaSyncService
from convertreino.domain.exceptions import StravaApiError, StravaAuthError, UserNotFoundError
from convertreino.infrastructure.repositories.in_memory_activity_repository import (
    InMemoryActivityRepository,
)
from convertreino.infrastructure.repositories.in_memory_user_repository import (
    InMemoryUserRepository,
)
from convertreino.infrastructure.strava.fake_client import FakeStravaApiClient
from tests.builders import build_activity, build_strava_activity_summary, build_user

CLIENT_ID = "test-client-id"
REDIRECT_URI = "http://localhost:8000/auth/strava/callback"
ATHLETE_ID = 99_001


def _linked_user(**kwargs: object):
    defaults = {
        "strava_athlete_id": ATHLETE_ID,
        "access_token": "valid-access",
        "refresh_token": "valid-refresh",
        "token_expires_at": datetime.now(UTC) + timedelta(hours=1),
    }
    defaults.update(kwargs)
    return build_user(**defaults)  # type: ignore[arg-type]


def _service(
    user_repo: InMemoryUserRepository,
    activity_repo: InMemoryActivityRepository,
    client: FakeStravaApiClient,
) -> StravaSyncService:
    from convertreino.application.strava_oauth_service import StravaOAuthService

    oauth = StravaOAuthService(
        user_repo=user_repo,
        strava_client=client,
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
    )
    return StravaSyncService(
        user_repo=user_repo,
        activity_repo=activity_repo,
        strava_client=client,
        oauth_service=oauth,
    )


def test_first_sync_creates_all_activities():
    # Arrange — CN-1
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    activities = [
        build_strava_activity_summary(id=101, distance=5000),
        build_strava_activity_summary(id=102, distance=6000),
        build_strava_activity_summary(id=103, distance=7000),
    ]
    client = FakeStravaApiClient(activities=activities)
    service = _service(user_repo, activity_repo, client)

    # Act
    result = service.sync_user(user.id)

    # Assert
    assert result.created_count == 3
    assert result.updated_count == 0
    assert result.synced_count == 3
    assert result.skipped_count == 0
    stored = activity_repo.get_all(user.id)
    assert len(stored) == 3
    assert all(activity.external_id is not None for activity in stored)


def test_resync_updates_existing_activities_without_duplicates():
    # Arrange — CN-2
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    activities = [
        build_strava_activity_summary(id=201),
        build_strava_activity_summary(id=202),
        build_strava_activity_summary(id=203),
    ]
    client = FakeStravaApiClient(activities=activities)
    service = _service(user_repo, activity_repo, client)
    service.sync_user(user.id)

    # Act
    result = service.sync_user(user.id)

    # Assert
    assert result.created_count == 0
    assert result.updated_count == 3
    assert result.synced_count == 3
    assert len(activity_repo.get_all(user.id)) == 3


def test_paginated_history_imports_all_activities():
    # Arrange — CN-3
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    activities = [build_strava_activity_summary(id=i) for i in range(250)]
    client = FakeStravaApiClient(activities=activities)
    service = _service(user_repo, activity_repo, client)

    # Act
    result = service.sync_user(user.id)

    # Assert
    assert result.created_count == 250
    assert len(activity_repo.get_all(user.id)) == 250
    assert client.list_activities_calls == [(1, 200), (2, 200)]


def test_empty_strava_list_returns_zero_counts():
    # Arrange — CB-1
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    client = FakeStravaApiClient(activities=[])
    service = _service(user_repo, activity_repo, client)

    # Act
    result = service.sync_user(user.id)

    # Assert
    assert result.synced_count == 0
    assert result.created_count == 0
    assert result.updated_count == 0
    assert result.skipped_count == 0


def test_zero_distance_activity_is_persisted():
    # Arrange — CB-2
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    client = FakeStravaApiClient(
        activities=[build_strava_activity_summary(id=301, distance=0.0)]
    )
    service = _service(user_repo, activity_repo, client)

    # Act
    result = service.sync_user(user.id)

    # Assert
    assert result.created_count == 1
    assert activity_repo.get_all(user.id)[0].distance_meters == 0.0


def test_refreshes_token_before_sync_when_expiring_soon():
    # Arrange — CB-3
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user(
        token_expires_at=datetime.now(UTC) + timedelta(minutes=2),
    )
    user_repo.save(user)
    client = FakeStravaApiClient(
        athlete_id=ATHLETE_ID,
        activities=[build_strava_activity_summary(id=401)],
    )
    service = _service(user_repo, activity_repo, client)

    # Act
    service.sync_user(user.id)

    # Assert
    assert client.refresh_calls == ["valid-refresh"]
    persisted = user_repo.get_by_id(user.id)
    assert persisted is not None
    assert persisted.access_token == "fake-access-token-refreshed"


def test_resync_updates_changed_distance_preserving_internal_id():
    # Arrange — CB-4
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    existing = build_activity(user_id=user.id, external_id="501", distance_meters=1000.0)
    activity_repo.save(existing)
    client = FakeStravaApiClient(
        activities=[build_strava_activity_summary(id=501, distance=9999.0)]
    )
    service = _service(user_repo, activity_repo, client)

    # Act
    result = service.sync_user(user.id)

    # Assert
    assert result.updated_count == 1
    stored = activity_repo.get_by_external_id(user.id, "501")
    assert stored is not None
    assert stored.id == existing.id
    assert stored.distance_meters == 9999.0


def test_invalid_strava_activity_is_skipped():
    # Arrange — CB-5
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    client = FakeStravaApiClient(
        activities=[
            build_strava_activity_summary(id=601, distance=-1.0),
            build_strava_activity_summary(id=602),
        ]
    )
    service = _service(user_repo, activity_repo, client)

    # Act
    result = service.sync_user(user.id)

    # Assert
    assert result.skipped_count == 1
    assert result.created_count == 1
    assert len(activity_repo.get_all(user.id)) == 1


def test_raises_user_not_found_for_unknown_user_id():
    # Arrange — CE-1
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    client = FakeStravaApiClient()
    service = _service(user_repo, activity_repo, client)

    # Act / Assert
    with pytest.raises(UserNotFoundError):
        service.sync_user(uuid4())


def test_raises_strava_auth_error_when_user_has_no_strava_link():
    # Arrange — CE-2
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = build_user()
    user_repo.save(user)
    client = FakeStravaApiClient()
    service = _service(user_repo, activity_repo, client)

    # Act / Assert
    with pytest.raises(StravaAuthError, match="no linked Strava"):
        service.sync_user(user.id)


def test_raises_strava_auth_error_when_list_activities_returns_401():
    # Arrange — CE-3
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    client = FakeStravaApiClient(
        activities=[build_strava_activity_summary(id=701)],
        fail_list_auth_pages={1},
    )
    service = _service(user_repo, activity_repo, client)

    # Act / Assert
    with pytest.raises(StravaAuthError, match="Reauthorize"):
        service.sync_user(user.id)


def test_raises_strava_api_error_on_server_failure():
    # Arrange — CE-4
    user_repo = InMemoryUserRepository()
    activity_repo = InMemoryActivityRepository()
    user = _linked_user()
    user_repo.save(user)
    client = FakeStravaApiClient(
        activities=[build_strava_activity_summary(id=801 + i) for i in range(201)],
        fail_list_server_pages={2},
    )
    service = _service(user_repo, activity_repo, client)

    # Act / Assert
    with pytest.raises(StravaApiError):
        service.sync_user(user.id)
    assert len(activity_repo.get_all(user.id)) == 200

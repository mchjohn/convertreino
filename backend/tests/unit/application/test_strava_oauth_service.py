from datetime import UTC, datetime, timedelta

import pytest

from convertreino.application.strava_oauth_service import StravaOAuthService
from convertreino.domain.exceptions import StravaAuthError
from convertreino.infrastructure.repositories.in_memory_user_repository import (
    InMemoryUserRepository,
)
from convertreino.infrastructure.strava.fake_client import FakeStravaApiClient
from tests.builders import build_user

CLIENT_ID = "test-client-id"
REDIRECT_URI = "http://localhost:8000/auth/strava/callback"
ATHLETE_ID = 99_001


def _service(
    repo: InMemoryUserRepository,
    client: FakeStravaApiClient,
) -> StravaOAuthService:
    return StravaOAuthService(
        user_repo=repo,
        strava_client=client,
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
    )


def test_exchange_code_creates_user_with_strava_fields():
    # Arrange — CN-1
    repo = InMemoryUserRepository()
    client = FakeStravaApiClient(athlete_id=ATHLETE_ID)
    service = _service(repo, client)

    # Act
    user = service.exchange_code("valid-code")

    # Assert
    assert user.strava_athlete_id == ATHLETE_ID
    assert user.access_token == "fake-access-token"
    assert user.refresh_token == "fake-refresh-token"
    assert user.token_expires_at is not None
    assert repo.get_by_strava_athlete_id(ATHLETE_ID) == user


def test_exchange_code_updates_existing_user_tokens_preserving_id():
    # Arrange — CN-2
    repo = InMemoryUserRepository()
    existing = build_user(
        strava_athlete_id=ATHLETE_ID,
        access_token="old-access",
        refresh_token="old-refresh",
        token_expires_at=datetime.now(UTC),
    )
    repo.save(existing)
    client = FakeStravaApiClient(athlete_id=ATHLETE_ID, access_token="new-access")
    service = _service(repo, client)

    # Act
    user = service.exchange_code("valid-code")

    # Assert
    assert user.id == existing.id
    assert user.access_token == "new-access"
    assert repo.get_by_strava_athlete_id(ATHLETE_ID) is not None
    assert repo.get_by_id(existing.id) is not None


def test_get_authorization_url_contains_required_params():
    # Arrange — CN-3
    repo = InMemoryUserRepository()
    client = FakeStravaApiClient()
    service = _service(repo, client)

    # Act
    url = service.get_authorization_url()

    # Assert
    assert "client_id=test-client-id" in url
    assert "redirect_uri=" in url
    assert "response_type=code" in url
    assert "scope=" in url


def test_ensure_valid_token_returns_user_when_token_not_expiring_soon():
    # Arrange — CN-4
    repo = InMemoryUserRepository()
    user = build_user(
        strava_athlete_id=ATHLETE_ID,
        access_token="valid-access",
        refresh_token="valid-refresh",
        token_expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    repo.save(user)
    client = FakeStravaApiClient()
    service = _service(repo, client)

    # Act
    result = service.ensure_valid_token(user)

    # Assert
    assert result == user
    assert client.refresh_calls == []


def test_ensure_valid_token_refreshes_when_expiring_within_five_minutes():
    # Arrange — CB-1
    repo = InMemoryUserRepository()
    user = build_user(
        strava_athlete_id=ATHLETE_ID,
        access_token="expiring-access",
        refresh_token="valid-refresh",
        token_expires_at=datetime.now(UTC) + timedelta(minutes=2),
    )
    repo.save(user)
    client = FakeStravaApiClient(athlete_id=ATHLETE_ID)
    service = _service(repo, client)

    # Act
    result = service.ensure_valid_token(user)

    # Assert
    assert client.refresh_calls == ["valid-refresh"]
    assert result.access_token == "fake-access-token-refreshed"
    assert result.id == user.id
    persisted = repo.get_by_id(user.id)
    assert persisted is not None
    assert persisted.access_token == "fake-access-token-refreshed"


def test_second_exchange_overwrites_tokens_for_same_athlete():
    # Arrange — CB-2
    repo = InMemoryUserRepository()
    first_client = FakeStravaApiClient(athlete_id=ATHLETE_ID, access_token="first-token")
    service = _service(repo, first_client)
    first = service.exchange_code("code-1")

    second_client = FakeStravaApiClient(athlete_id=ATHLETE_ID, access_token="second-token")
    service = _service(repo, second_client)

    # Act
    second = service.exchange_code("code-2")

    # Assert
    assert second.id == first.id
    assert second.access_token == "second-token"
    assert repo.get_by_strava_athlete_id(ATHLETE_ID) is not None


def test_exchange_code_raises_strava_auth_error_on_invalid_code():
    # Arrange — CE-1
    repo = InMemoryUserRepository()
    client = FakeStravaApiClient(fail_exchange=True)
    service = _service(repo, client)

    # Act / Assert
    with pytest.raises(StravaAuthError):
        service.exchange_code("invalid-code")
    assert repo.get_by_strava_athlete_id(ATHLETE_ID) is None


def test_ensure_valid_token_raises_when_refresh_fails():
    # Arrange — CE-2
    repo = InMemoryUserRepository()
    user = build_user(
        strava_athlete_id=ATHLETE_ID,
        access_token="expiring-access",
        refresh_token="bad-refresh",
        token_expires_at=datetime.now(UTC) + timedelta(minutes=1),
    )
    repo.save(user)
    client = FakeStravaApiClient(fail_refresh=True)
    service = _service(repo, client)

    # Act / Assert
    with pytest.raises(StravaAuthError):
        service.ensure_valid_token(user)


def test_exchange_code_does_not_persist_on_strava_server_error():
    # Arrange — CE-3
    repo = InMemoryUserRepository()
    client = FakeStravaApiClient(fail_server_error=True)
    service = _service(repo, client)

    # Act / Assert
    with pytest.raises(StravaAuthError, match="unavailable"):
        service.exchange_code("any-code")
    assert repo.get_by_strava_athlete_id(ATHLETE_ID) is None


def test_ensure_valid_token_raises_when_user_has_no_tokens():
    # Arrange
    repo = InMemoryUserRepository()
    user = build_user()
    repo.save(user)
    client = FakeStravaApiClient()
    service = _service(repo, client)

    # Act / Assert
    with pytest.raises(StravaAuthError, match="no Strava tokens"):
        service.ensure_valid_token(user)

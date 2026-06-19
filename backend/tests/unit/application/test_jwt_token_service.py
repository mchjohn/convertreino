from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest

from convertreino.application.jwt_token_service import JwtSettings, JwtTokenService
from convertreino.domain.exceptions import InvalidTokenError

TEST_SECRET = "test-jwt-secret-key-for-unit-tests"
USER_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _service(*, expires_minutes: int = 60) -> JwtTokenService:
    return JwtTokenService(JwtSettings(secret=TEST_SECRET, expires_minutes=expires_minutes))


def test_create_and_decode_round_trip_returns_same_user_id():
    # Arrange — CN-3
    service = _service()

    # Act
    token = service.create_access_token(USER_ID)
    decoded = service.decode_access_token(token)

    # Assert
    assert decoded == USER_ID


def test_create_access_token_and_decode_access_token_contract():
    # Arrange — contrato de assinatura
    service = _service()

    # Act
    token = service.create_access_token(USER_ID)
    payload = jwt.decode(token, TEST_SECRET, algorithms=["HS256"])

    # Assert
    assert payload["sub"] == str(USER_ID)
    assert "iat" in payload
    assert "exp" in payload
    assert service.decode_access_token(token) == USER_ID


def test_token_near_expiration_still_valid():
    # Arrange — CB-2
    settings = JwtSettings(secret=TEST_SECRET, expires_minutes=60)
    service = JwtTokenService(settings)
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(USER_ID),
            "iat": now - timedelta(minutes=59),
            "exp": now + timedelta(minutes=1),
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    # Act
    decoded = service.decode_access_token(token)

    # Assert
    assert decoded == USER_ID


def test_decode_raises_on_malformed_token():
    # Arrange — CE-2
    service = _service()

    # Act / Assert
    with pytest.raises(InvalidTokenError):
        service.decode_access_token("not-a-jwt")


def test_decode_raises_on_invalid_signature():
    # Arrange — CE-2
    service = _service()
    token = jwt.encode({"sub": str(USER_ID)}, "other-secret", algorithm="HS256")

    # Act / Assert
    with pytest.raises(InvalidTokenError):
        service.decode_access_token(token)


def test_decode_raises_on_expired_token():
    # Arrange — CE-3
    service = _service()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(USER_ID),
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    # Act / Assert
    with pytest.raises(InvalidTokenError):
        service.decode_access_token(token)


def test_decode_raises_when_sub_missing():
    # Arrange — CE-2
    service = _service()
    token = jwt.encode(
        {"exp": datetime.now(UTC) + timedelta(hours=1)},
        TEST_SECRET,
        algorithm="HS256",
    )

    # Act / Assert
    with pytest.raises(InvalidTokenError):
        service.decode_access_token(token)


def test_decode_raises_when_sub_not_uuid():
    # Arrange — CE-2
    service = _service()
    token = jwt.encode(
        {"sub": "not-a-uuid", "exp": datetime.now(UTC) + timedelta(hours=1)},
        TEST_SECRET,
        algorithm="HS256",
    )

    # Act / Assert
    with pytest.raises(InvalidTokenError):
        service.decode_access_token(token)


def test_init_raises_when_secret_empty():
    # Arrange — CE-5
    settings = JwtSettings(secret="", expires_minutes=60)

    # Act / Assert
    with pytest.raises(ValueError, match="JWT_SECRET"):
        JwtTokenService(settings)


def test_two_tokens_for_same_user_decode_to_same_sub():
    # Arrange — CB-1 (unit slice: re-emissão preserva sub)
    service = _service()
    user_id = uuid4()

    # Act
    first = service.create_access_token(user_id)
    second = service.create_access_token(user_id)

    # Assert
    assert service.decode_access_token(first) == user_id
    assert service.decode_access_token(second) == user_id

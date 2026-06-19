from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from convertreino.api.dependencies import get_current_user_id
from convertreino.application.jwt_token_service import JwtSettings, JwtTokenService
from convertreino.domain.exceptions import InvalidTokenError

TEST_SECRET = "test-jwt-secret-key-for-unit-tests"
USER_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _service() -> JwtTokenService:
    return JwtTokenService(JwtSettings(secret=TEST_SECRET, expires_minutes=60))


def test_get_current_user_id_returns_sub_from_valid_bearer_token():
    # Arrange
    service = _service()
    token = service.create_access_token(USER_ID)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    # Act
    result = get_current_user_id(credentials=credentials, jwt_service=service)

    # Assert
    assert result == USER_ID


def test_get_current_user_id_raises_401_when_credentials_missing():
    # Arrange — CE-1
    service = _service()

    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(credentials=None, jwt_service=service)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Not authenticated"


def test_get_current_user_id_raises_401_when_scheme_not_bearer():
    # Arrange
    service = _service()
    credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="abc")

    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(credentials=credentials, jwt_service=service)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Not authenticated"


def test_get_current_user_id_raises_401_on_invalid_token():
    # Arrange — CE-2
    service = _service()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")

    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(credentials=credentials, jwt_service=service)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid or expired token"


def test_get_current_user_id_raises_401_on_expired_token():
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
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(credentials=credentials, jwt_service=service)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid or expired token"


def test_invalid_token_error_maps_to_http_401_detail():
    # Arrange — contrato API
    service = _service()

    # Act / Assert
    with pytest.raises(InvalidTokenError):
        service.decode_access_token("bad-token")

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(credentials=credentials, jwt_service=service)
    assert exc_info.value.status_code == 401


def test_get_current_user_id_accepts_lowercase_bearer_scheme():
    # Arrange
    service = _service()
    token = service.create_access_token(uuid4())
    credentials = HTTPAuthorizationCredentials(scheme="bearer", credentials=token)

    # Act
    result = get_current_user_id(credentials=credentials, jwt_service=service)

    # Assert
    assert isinstance(result, UUID)

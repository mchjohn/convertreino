from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from convertreino.domain.exceptions import InvalidTokenError


@dataclass(frozen=True, slots=True)
class JwtSettings:
    secret: str
    expires_minutes: int


class JwtTokenService:
    def __init__(self, settings: JwtSettings) -> None:
        if not settings.secret:
            raise ValueError("JWT_SECRET must be set")
        self._settings = settings

    def create_access_token(self, user_id: UUID) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=self._settings.expires_minutes),
        }
        return jwt.encode(payload, self._settings.secret, algorithm="HS256")

    def decode_access_token(self, token: str) -> UUID:
        try:
            payload = jwt.decode(
                token,
                self._settings.secret,
                algorithms=["HS256"],
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc

        sub = payload.get("sub")
        if sub is None:
            raise InvalidTokenError("missing sub claim")
        try:
            return UUID(str(sub))
        except (ValueError, TypeError) as exc:
            raise InvalidTokenError("invalid sub claim") from exc

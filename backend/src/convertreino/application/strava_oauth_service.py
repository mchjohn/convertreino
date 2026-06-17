from datetime import UTC, datetime, timedelta
from uuid import uuid4

from convertreino.domain.entities.user import User
from convertreino.domain.exceptions import StravaAuthError
from convertreino.domain.repositories.user_repository import UserRepository
from convertreino.infrastructure.config import build_authorization_url
from convertreino.infrastructure.strava.client import StravaApiClient

TOKEN_REFRESH_MARGIN = timedelta(minutes=5)


class StravaOAuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        strava_client: StravaApiClient,
        *,
        client_id: str,
        redirect_uri: str,
    ) -> None:
        self._user_repo = user_repo
        self._strava_client = strava_client
        self._client_id = client_id
        self._redirect_uri = redirect_uri

    def get_authorization_url(self) -> str:
        return build_authorization_url(
            client_id=self._client_id,
            redirect_uri=self._redirect_uri,
        )

    def exchange_code(self, code: str) -> User:
        try:
            token_response = self._strava_client.exchange_code(code)
        except StravaAuthError:
            raise

        existing = self._user_repo.get_by_strava_athlete_id(token_response.athlete_id)
        if existing is None:
            user = User(
                id=uuid4(),
                created_at=datetime.now(UTC),
                strava_athlete_id=token_response.athlete_id,
                access_token=token_response.access_token,
                refresh_token=token_response.refresh_token,
                token_expires_at=token_response.expires_at,
            )
        else:
            user = User(
                id=existing.id,
                created_at=existing.created_at,
                strava_athlete_id=token_response.athlete_id,
                access_token=token_response.access_token,
                refresh_token=token_response.refresh_token,
                token_expires_at=token_response.expires_at,
            )

        return self._user_repo.save(user)

    def ensure_valid_token(self, user: User) -> User:
        if user.token_expires_at is None or user.refresh_token is None:
            raise StravaAuthError("User has no Strava tokens")

        if user.token_expires_at >= datetime.now(UTC) + TOKEN_REFRESH_MARGIN:
            return user

        try:
            token_response = self._strava_client.refresh_token(user.refresh_token)
        except StravaAuthError:
            raise

        updated = User(
            id=user.id,
            created_at=user.created_at,
            strava_athlete_id=user.strava_athlete_id,
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            token_expires_at=token_response.expires_at,
        )
        return self._user_repo.save(updated)

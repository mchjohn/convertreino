import logging
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from convertreino.application.strava_oauth_service import StravaOAuthService
from convertreino.domain.entities.user import User
from convertreino.domain.exceptions import (
    StravaActivityNotFoundError,
    StravaApiError,
    StravaAuthError,
)
from convertreino.domain.repositories.activity_repository import ActivityRepository
from convertreino.domain.repositories.user_repository import UserRepository
from convertreino.infrastructure.strava.client import StravaApiClient
from convertreino.infrastructure.strava.mapper import map_strava_activity_to_domain
from convertreino.infrastructure.strava.webhook import StravaWebhookEvent

logger = logging.getLogger(__name__)

WebhookAction = Literal["created", "updated", "deleted", "deauthorized", "ignored"]


@dataclass(frozen=True, slots=True)
class WebhookResult:
    action: WebhookAction
    user_id: UUID | None


class StravaWebhookProcessor:
    def __init__(
        self,
        user_repo: UserRepository,
        activity_repo: ActivityRepository,
        strava_client: StravaApiClient,
        oauth_service: StravaOAuthService,
    ) -> None:
        self._user_repo = user_repo
        self._activity_repo = activity_repo
        self._strava_client = strava_client
        self._oauth_service = oauth_service

    def handle_event(self, event: StravaWebhookEvent) -> WebhookResult:
        user = self._user_repo.get_by_strava_athlete_id(event.owner_id)
        if user is None:
            logger.warning(
                "Ignoring Strava webhook for unknown athlete owner_id=%s",
                event.owner_id,
            )
            return WebhookResult(action="ignored", user_id=None)

        if event.object_type == "activity" and event.aspect_type in {"create", "update"}:
            return self._handle_activity_upsert(user, event)
        if event.object_type == "activity" and event.aspect_type == "delete":
            return self._handle_activity_delete(user, event)
        if (
            event.object_type == "athlete"
            and event.aspect_type == "update"
            and event.updates.get("authorized") == "false"
        ):
            return self._handle_athlete_deauth(user)

        logger.info(
            "Ignoring unhandled Strava webhook object_type=%s aspect_type=%s",
            event.object_type,
            event.aspect_type,
        )
        return WebhookResult(action="ignored", user_id=user.id)

    def _handle_activity_upsert(
        self,
        user: User,
        event: StravaWebhookEvent,
    ) -> WebhookResult:
        external_id = str(event.object_id)
        try:
            user = self._oauth_service.ensure_valid_token(user)
            access_token = user.access_token
            if access_token is None:
                raise StravaAuthError("User has no Strava tokens")

            summary = self._strava_client.get_activity(access_token, event.object_id)
        except StravaAuthError:
            logger.warning(
                "Ignoring Strava webhook create/update due to auth error activity_id=%s user=%s",
                event.object_id,
                user.id,
            )
            return WebhookResult(action="ignored", user_id=user.id)
        except StravaApiError:
            logger.error(
                "Ignoring Strava webhook create/update due to API error activity_id=%s user=%s",
                event.object_id,
                user.id,
            )
            return WebhookResult(action="ignored", user_id=user.id)
        except StravaActivityNotFoundError:
            return self._handle_activity_not_found(user, external_id)

        activity = map_strava_activity_to_domain(summary, user_id=user.id)
        if activity is None:
            logger.warning(
                "Ignoring invalid Strava activity id=%s for user=%s",
                event.object_id,
                user.id,
            )
            return WebhookResult(action="ignored", user_id=user.id)

        existing = self._activity_repo.get_by_external_id(user.id, external_id)
        self._activity_repo.upsert(activity)
        action: WebhookAction = "created" if existing is None else "updated"
        return WebhookResult(action=action, user_id=user.id)

    def _handle_activity_delete(self, user: User, event: StravaWebhookEvent) -> WebhookResult:
        external_id = str(event.object_id)
        self._activity_repo.delete_by_external_id(user.id, external_id)
        return WebhookResult(action="deleted", user_id=user.id)

    def _handle_activity_not_found(self, user: User, external_id: str) -> WebhookResult:
        existing = self._activity_repo.get_by_external_id(user.id, external_id)
        if existing is not None:
            self._activity_repo.delete_by_external_id(user.id, external_id)
            return WebhookResult(action="deleted", user_id=user.id)
        return WebhookResult(action="ignored", user_id=user.id)

    def _handle_athlete_deauth(self, user: User) -> WebhookResult:
        cleared = User(
            id=user.id,
            created_at=user.created_at,
            strava_athlete_id=user.strava_athlete_id,
            access_token=None,
            refresh_token=None,
            token_expires_at=None,
        )
        self._user_repo.save(cleared)
        return WebhookResult(action="deauthorized", user_id=user.id)

import logging
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from convertreino.application.strava_oauth_service import StravaOAuthService
from convertreino.domain.exceptions import StravaAuthError, UserNotFoundError
from convertreino.domain.repositories.activity_repository import ActivityRepository
from convertreino.domain.repositories.user_repository import UserRepository
from convertreino.infrastructure.strava.client import StravaApiClient
from convertreino.infrastructure.strava.mapper import map_strava_activity_to_domain

logger = logging.getLogger(__name__)

PER_PAGE = 200
MAX_PAGES = 500


@dataclass(frozen=True, slots=True)
class SyncResult:
    synced_count: int
    created_count: int
    updated_count: int
    skipped_count: int


class StravaSyncService:
    def __init__(
        self,
        user_repo: UserRepository,
        activity_repo: ActivityRepository,
        strava_client: StravaApiClient,
        oauth_service: StravaOAuthService,
        *,
        page_commit: Callable[[], None] | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._activity_repo = activity_repo
        self._strava_client = strava_client
        self._oauth_service = oauth_service
        self._page_commit = page_commit

    def sync_user(self, user_id: UUID) -> SyncResult:
        user = self._user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User not found: {user_id}")

        if (
            user.strava_athlete_id is None
            or user.access_token is None
            or user.refresh_token is None
            or user.token_expires_at is None
        ):
            raise StravaAuthError("User has no linked Strava account")

        user = self._oauth_service.ensure_valid_token(user)
        access_token = user.access_token
        if access_token is None:
            raise StravaAuthError("User has no Strava tokens")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for page in range(1, MAX_PAGES + 1):
            summaries = self._strava_client.list_activities(
                access_token,
                page=page,
                per_page=PER_PAGE,
            )
            if not summaries:
                break

            for summary in summaries:
                activity = map_strava_activity_to_domain(summary, user_id=user_id)
                if activity is None:
                    skipped_count += 1
                    logger.warning(
                        "Skipping invalid Strava activity id=%s for user=%s",
                        summary.id,
                        user_id,
                    )
                    continue

                existing = self._activity_repo.get_by_external_id(
                    user_id,
                    activity.external_id,  # type: ignore[arg-type]
                )
                self._activity_repo.upsert(activity)
                if existing is None:
                    created_count += 1
                else:
                    updated_count += 1

            if self._page_commit is not None:
                self._page_commit()

            if len(summaries) < PER_PAGE:
                break

            if page == MAX_PAGES:
                logger.warning(
                    "Strava sync reached MAX_PAGES=%s for user=%s",
                    MAX_PAGES,
                    user_id,
                )

        synced_count = created_count + updated_count
        return SyncResult(
            synced_count=synced_count,
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
        )

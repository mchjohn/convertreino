from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from convertreino.api.dependencies import get_strava_sync_service
from convertreino.application.strava_sync_service import StravaSyncService, SyncResult
from convertreino.domain.exceptions import StravaApiError, StravaAuthError, UserNotFoundError

router = APIRouter(prefix="/users", tags=["strava-sync"])


@router.post("/{user_id}/sync/strava")
def sync_strava(
    user_id: UUID,
    sync_service: StravaSyncService = Depends(get_strava_sync_service),  # noqa: B008
) -> SyncResult:
    try:
        return sync_service.sync_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc
    except StravaAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StravaApiError as exc:
        raise HTTPException(status_code=502, detail="Strava API unavailable") from exc
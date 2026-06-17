from fastapi import APIRouter, Depends, HTTPException, Query

from convertreino.api.dependencies import get_strava_oauth_service
from convertreino.application.strava_oauth_service import StravaOAuthService
from convertreino.domain.exceptions import StravaAuthError

router = APIRouter(prefix="/auth/strava", tags=["strava-auth"])


@router.get("/authorize")
def authorize(
    oauth_service: StravaOAuthService = Depends(get_strava_oauth_service),
) -> dict[str, str]:
    return {"authorization_url": oauth_service.get_authorization_url()}


@router.get("/callback")
def callback(
    code: str = Query(...),
    oauth_service: StravaOAuthService = Depends(get_strava_oauth_service),
) -> dict[str, str]:
    try:
        user = oauth_service.exchange_code(code)
    except StravaAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"user_id": str(user.id)}

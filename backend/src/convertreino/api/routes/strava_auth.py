from fastapi import APIRouter, Depends, HTTPException, Query

from convertreino.api.dependencies import get_jwt_token_service, get_strava_oauth_service
from convertreino.application.jwt_token_service import JwtTokenService
from convertreino.application.strava_oauth_service import StravaOAuthService
from convertreino.domain.exceptions import StravaAuthError
from convertreino.infrastructure.config import get_jwt_settings

router = APIRouter(prefix="/auth/strava", tags=["strava-auth"])


@router.get("/authorize")
def authorize(
    oauth_service: StravaOAuthService = Depends(get_strava_oauth_service),  # noqa: B008
) -> dict[str, str]:
    return {"authorization_url": oauth_service.get_authorization_url()}


@router.get("/callback")
def callback(
    code: str = Query(...),
    oauth_service: StravaOAuthService = Depends(get_strava_oauth_service),  # noqa: B008
    jwt_service: JwtTokenService = Depends(get_jwt_token_service),  # noqa: B008
) -> dict[str, str | int]:
    try:
        user = oauth_service.exchange_code(code)
    except StravaAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    jwt_settings = get_jwt_settings()
    access_token = jwt_service.create_access_token(user.id)
    return {
        "user_id": str(user.id),
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": jwt_settings.expires_minutes * 60,
    }

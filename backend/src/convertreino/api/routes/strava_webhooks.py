from fastapi import APIRouter, Depends, HTTPException, Query, Request

from convertreino.api.dependencies import (
    get_strava_webhook_processor,
    get_strava_webhook_settings_dep,
)
from convertreino.application.strava_webhook_processor import StravaWebhookProcessor, WebhookResult
from convertreino.infrastructure.config import StravaWebhookSettings
from convertreino.infrastructure.strava.webhook import parse_strava_webhook_event

router = APIRouter(prefix="/webhooks", tags=["strava-webhooks"])


@router.get("/strava")
def validate_strava_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    settings: StravaWebhookSettings = Depends(get_strava_webhook_settings_dep),  # noqa: B008
) -> dict[str, str]:
    if hub_verify_token != settings.verify_token:
        raise HTTPException(status_code=403, detail="Invalid verify token")
    if hub_mode != "subscribe":
        raise HTTPException(status_code=403, detail="Invalid verify token")
    return {"hub.challenge": hub_challenge}


@router.post("/strava")
async def receive_strava_webhook(
    request: Request,
    processor: StravaWebhookProcessor = Depends(get_strava_webhook_processor),  # noqa: B008
) -> WebhookResult:
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    try:
        event = parse_strava_webhook_event(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc

    return processor.handle_event(event)

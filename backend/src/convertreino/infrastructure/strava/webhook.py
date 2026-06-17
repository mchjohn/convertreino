from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class StravaWebhookEvent:
    object_type: str
    aspect_type: str
    object_id: int
    owner_id: int
    event_time: int
    subscription_id: int
    updates: dict[str, Any]


def _require_int(data: dict[str, object], key: str) -> int:
    if key not in data:
        raise ValueError("Invalid webhook payload")
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise ValueError("Invalid webhook payload")
    return int(value)


def parse_strava_webhook_event(data: dict[str, object]) -> StravaWebhookEvent:
    try:
        object_type = str(data["object_type"])
        aspect_type = str(data["aspect_type"])
        object_id = _require_int(data, "object_id")
        owner_id = _require_int(data, "owner_id")
        event_time = _require_int(data, "event_time")
        subscription_id = _require_int(data, "subscription_id")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid webhook payload") from exc

    updates_raw = data.get("updates", {})
    if updates_raw is None:
        updates: dict[str, Any] = {}
    elif not isinstance(updates_raw, dict):
        raise ValueError("Invalid webhook payload")
    else:
        updates = dict(updates_raw)

    return StravaWebhookEvent(
        object_type=object_type,
        aspect_type=aspect_type,
        object_id=object_id,
        owner_id=owner_id,
        event_time=event_time,
        subscription_id=subscription_id,
        updates=updates,
    )

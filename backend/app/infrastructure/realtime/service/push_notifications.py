import asyncio
import json
import urllib.error
import urllib.request

import logfire

from app.core.config import settings
from app.domains.announcements.models import Announcement

FCM_ENDPOINT = "https://fcm.googleapis.com/fcm/send"


def _fcm_headers(server_key: str) -> dict[str, str]:
    return {
        "Authorization": f"key={server_key}",
        "Content-Type": "application/json",
    }


def _build_fcm_payload(announcement: Announcement, event: str, topic: str) -> dict[str, object]:
    return {
        "to": f"/topics/{topic}",
        "priority": "high",
        "notification": {
            "title": announcement.title,
            "body": announcement.body,
        },
        "data": {
            "event": event,
            "announcement_id": str(announcement.id),
            "priority": announcement.priority,
            "published_at": announcement.published_at.isoformat(),
            "is_pinned": announcement.is_pinned,
        },
    }


def _post_json(url: str, *, headers: dict[str, str], body: dict[str, object]) -> tuple[int, str]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.status, response.read().decode("utf-8")


async def publish_announcement_push(announcement: Announcement, *, event: str) -> None:
    server_key = settings.FCM_SERVER_KEY.strip()
    topic = settings.FCM_TOPIC.strip() or "participants"

    if not server_key:
        return

    payload = _build_fcm_payload(announcement, event, topic)

    try:
        status, response_body = await asyncio.to_thread(
            _post_json,
            FCM_ENDPOINT,
            headers=_fcm_headers(server_key),
            body=payload,
        )
        if status >= 400:
            logfire.warn("FCM push request failed", status_code=status, response_body=response_body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logfire.warn("FCM HTTP error", status_code=exc.code, response_body=body)
    except Exception as exc:
        logfire.warn("Failed to publish FCM push notification", error=str(exc))

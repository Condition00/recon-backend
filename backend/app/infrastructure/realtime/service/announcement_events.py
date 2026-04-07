import json
import uuid
from datetime import datetime

from redis.asyncio import Redis

from app.domains.announcements.models import Announcement

ANNOUNCEMENTS_CHANNEL = "announcements.live"


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


async def publish_announcement_upserted(redis: Redis, *, event: str, announcement: Announcement) -> None:
    payload = {
        "event": event,
        "announcement": {
            "id": str(announcement.id),
            "title": announcement.title,
            "body": announcement.body,
            "priority": announcement.priority,
            "published_at": _iso(announcement.published_at),
            "expires_at": _iso(announcement.expires_at),
            "is_pinned": announcement.is_pinned,
            "created_by": str(announcement.created_by),
            "created_at": _iso(announcement.created_at),
            "updated_at": _iso(announcement.updated_at),
        },
    }
    await redis.publish(ANNOUNCEMENTS_CHANNEL, json.dumps(payload))


async def publish_announcement_deleted(redis: Redis, *, announcement_id: uuid.UUID) -> None:
    payload = {
        "event": "announcement.deleted",
        "announcement": {"id": str(announcement_id)},
    }
    await redis.publish(ANNOUNCEMENTS_CHANNEL, json.dumps(payload))

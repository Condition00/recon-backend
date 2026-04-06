import uuid
from collections.abc import Awaitable, Callable

import logfire
from redis.asyncio import Redis
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.post_commit import add_post_commit_hook
from app.domains.announcements.models import Announcement
from app.domains.announcements.schemas import AnnouncementCreate, AnnouncementUpdate
from app.domains.announcements.service import (
    edit_announcement,
    get_active_announcement_or_404,
    list_announcements,
    publish_announcement,
    remove_announcement,
)
from app.infrastructure.realtime.service import (
    publish_announcement_deleted,
    publish_announcement_push,
    publish_announcement_upserted,
)


async def list_active(db: AsyncSession) -> list[Announcement]:
    return await list_announcements(db)


async def get_active(db: AsyncSession, announcement_id: uuid.UUID) -> Announcement:
    return await get_active_announcement_or_404(db, announcement_id)


async def create(db: AsyncSession, payload: AnnouncementCreate, created_by: uuid.UUID, redis: Redis) -> Announcement:
    announcement = await publish_announcement(db, payload=payload, created_by=created_by)
    add_post_commit_hook(
        db,
        _best_effort_hook(
            "announcement.created realtime",
            lambda: publish_announcement_upserted(redis, event="announcement.created", announcement=announcement),
        ),
    )
    add_post_commit_hook(
        db,
        _best_effort_hook(
            "announcement.created push",
            lambda: publish_announcement_push(announcement, event="announcement.created"),
        ),
    )
    return announcement


async def update(db: AsyncSession, announcement_id: uuid.UUID, payload: AnnouncementUpdate, redis: Redis) -> Announcement:
    announcement = await edit_announcement(db, announcement_id=announcement_id, payload=payload)
    add_post_commit_hook(
        db,
        _best_effort_hook(
            "announcement.updated realtime",
            lambda: publish_announcement_upserted(redis, event="announcement.updated", announcement=announcement),
        ),
    )
    add_post_commit_hook(
        db,
        _best_effort_hook(
            "announcement.updated push",
            lambda: publish_announcement_push(announcement, event="announcement.updated"),
        ),
    )
    return announcement


async def delete(db: AsyncSession, announcement_id: uuid.UUID, redis: Redis) -> None:
    await remove_announcement(db, announcement_id)
    add_post_commit_hook(
        db,
        _best_effort_hook(
            "announcement.deleted realtime",
            lambda: publish_announcement_deleted(redis, announcement_id=announcement_id),
        ),
    )


def _best_effort_hook(name: str, operation: Callable[[], Awaitable[None]]) -> Callable[[], Awaitable[None]]:
    async def _runner() -> None:
        try:
            await operation()
        except Exception:
            logfire.warn("Post-commit operation failed", operation=name)

    return _runner

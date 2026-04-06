import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.announcements.crud import (
    create_announcement,
    delete_announcement,
    get_announcement_by_id,
    list_active_announcements,
    update_announcement,
)
from app.domains.announcements.models import Announcement
from app.domains.announcements.schemas import AnnouncementCreate, AnnouncementUpdate


async def list_announcements(db: AsyncSession) -> list[Announcement]:
    now = datetime.now(timezone.utc)
    return await list_active_announcements(db, now=now)


async def get_announcement_or_404(db: AsyncSession, announcement_id: uuid.UUID) -> Announcement:
    announcement = await get_announcement_by_id(db, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return announcement


async def get_active_announcement_or_404(db: AsyncSession, announcement_id: uuid.UUID) -> Announcement:
    announcement = await get_announcement_or_404(db, announcement_id)

    now = datetime.now(timezone.utc)
    is_active = announcement.published_at <= now and (
        announcement.expires_at is None or announcement.expires_at > now
    )
    if not is_active:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return announcement


async def publish_announcement(
    db: AsyncSession, *, payload: AnnouncementCreate, created_by: uuid.UUID
) -> Announcement:
    _validate_publish_window(payload.published_at, payload.expires_at)
    now = datetime.now(timezone.utc)
    return await create_announcement(db, payload=payload, created_by=created_by, now=now)


async def edit_announcement(
    db: AsyncSession, *, announcement_id: uuid.UUID, payload: AnnouncementUpdate
) -> Announcement:
    announcement = await get_announcement_or_404(db, announcement_id)

    new_published_at = payload.published_at if payload.published_at is not None else announcement.published_at
    new_expires_at = payload.expires_at if payload.expires_at is not None else announcement.expires_at
    _validate_publish_window(new_published_at, new_expires_at)

    return await update_announcement(db, announcement, payload)


async def remove_announcement(db: AsyncSession, announcement_id: uuid.UUID) -> None:
    announcement = await get_announcement_or_404(db, announcement_id)
    await delete_announcement(db, announcement)


def _validate_publish_window(published_at: datetime | None, expires_at: datetime | None) -> None:
    if published_at is not None and expires_at is not None and expires_at <= published_at:
        raise HTTPException(status_code=422, detail="expires_at must be later than published_at")

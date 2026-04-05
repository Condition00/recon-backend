import uuid
from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.announcements.models import Announcement
from app.domains.announcements.schemas import AnnouncementCreate, AnnouncementUpdate


async def list_active_announcements(db: AsyncSession, *, now: datetime) -> list[Announcement]:
    query = (
        select(Announcement)
        .where(Announcement.published_at <= now)
        .where((Announcement.expires_at.is_(None)) | (Announcement.expires_at > now))
        .order_by(Announcement.is_pinned.desc(), Announcement.published_at.desc(), Announcement.created_at.desc())
    )
    result = await db.exec(query)
    return list(result.all())


async def get_announcement_by_id(db: AsyncSession, announcement_id: uuid.UUID) -> Announcement | None:
    return await db.get(Announcement, announcement_id)


async def create_announcement(
    db: AsyncSession, *, payload: AnnouncementCreate, created_by: uuid.UUID, now: datetime
) -> Announcement:
    announcement = Announcement(
        title=payload.title,
        body=payload.body,
        priority=payload.priority,
        published_at=payload.published_at or now,
        expires_at=payload.expires_at,
        is_pinned=payload.is_pinned,
        created_by=created_by,
    )
    db.add(announcement)
    await db.flush()
    await db.refresh(announcement)
    return announcement


async def update_announcement(db: AsyncSession, announcement: Announcement, payload: AnnouncementUpdate) -> Announcement:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(announcement, key, value)
    await db.flush()
    await db.refresh(announcement)
    return announcement


async def delete_announcement(db: AsyncSession, announcement: Announcement) -> None:
    await db.delete(announcement)
    await db.flush()

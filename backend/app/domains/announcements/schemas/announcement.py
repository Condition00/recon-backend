import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel

from app.domains.announcements.models import AnnouncementPriority


class AnnouncementCreate(SQLModel):
    title: str
    body: str
    priority: AnnouncementPriority = AnnouncementPriority.info
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_pinned: bool = False


class AnnouncementUpdate(SQLModel):
    title: Optional[str] = None
    body: Optional[str] = None
    priority: Optional[AnnouncementPriority] = None
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_pinned: Optional[bool] = None


class AnnouncementRead(SQLModel):
    id: uuid.UUID
    title: str
    body: str
    priority: AnnouncementPriority
    published_at: datetime
    expires_at: Optional[datetime]
    is_pinned: bool
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

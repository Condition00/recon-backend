import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.utils.models.base import Base


class AnnouncementPriority(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class AnnouncementBase(SQLModel):
    title: str = Field(max_length=200)
    body: str = Field(max_length=5000)
    priority: AnnouncementPriority = Field(default=AnnouncementPriority.info)
    published_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
    expires_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))
    is_pinned: bool = Field(default=False)


class Announcement(Base, AnnouncementBase, table=True):
    __tablename__ = "announcements"

    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)

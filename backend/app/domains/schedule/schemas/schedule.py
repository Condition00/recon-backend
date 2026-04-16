import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel

from app.domains.schedule.models import SessionType


class SpeakerCreate(SQLModel):
    name: str
    bio: Optional[str] = None
    org: Optional[str] = None
    photo_key: Optional[str] = None


class SpeakerUpdate(SQLModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    org: Optional[str] = None
    photo_key: Optional[str] = None


class SpeakerRead(SQLModel):
    id: uuid.UUID
    name: str
    bio: Optional[str]
    org: Optional[str]
    photo_key: Optional[str]
    created_at: datetime
    updated_at: datetime


class SessionCreate(SQLModel):
    title: str
    description: Optional[str] = None
    starts_at: datetime
    ends_at: datetime
    session_type: SessionType = SessionType.talk
    zone_id: Optional[uuid.UUID] = None
    capacity: Optional[int] = None
    is_published: bool = False
    tags: Optional[list[str]] = None


class SessionUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    session_type: Optional[SessionType] = None
    zone_id: Optional[uuid.UUID] = None
    capacity: Optional[int] = None
    is_published: Optional[bool] = None
    tags: Optional[list[str]] = None


class SessionRead(SQLModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    starts_at: datetime
    ends_at: datetime
    session_type: SessionType
    zone_id: Optional[uuid.UUID]
    capacity: Optional[int]
    is_published: bool
    tags: Optional[list[str]]
    created_at: datetime
    updated_at: datetime


class SessionDetailRead(SessionRead):
    speakers: list[SpeakerRead] = []
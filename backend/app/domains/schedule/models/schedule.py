import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON

from app.utils.models.base import Base


class SessionType(str, Enum):
    talk = "talk"
    workshop = "workshop"
    ctf_round = "ctf_round"
    ceremony = "ceremony"
    break_ = "break"
    social = "social"


class SessionBase(SQLModel):
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    starts_at: datetime = Field(sa_type=DateTime(timezone=True))
    ends_at: datetime = Field(sa_type=DateTime(timezone=True))
    session_type: SessionType = Field(default=SessionType.talk)
    zone_id: Optional[uuid.UUID] = Field(default=None)
    capacity: Optional[int] = Field(default=None)
    is_published: bool = Field(default=False)
    tags: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))


class Session(Base, SessionBase, table=True):
    __tablename__ = "sessions"


class SpeakerBase(SQLModel):
    name: str = Field(max_length=200)
    bio: Optional[str] = Field(default=None, max_length=2000)
    org: Optional[str] = Field(default=None, max_length=200)
    photo_key: Optional[str] = Field(default=None)


class Speaker(Base, SpeakerBase, table=True):
    __tablename__ = "speakers"


class SessionSpeakerBase(SQLModel):
    session_id: uuid.UUID = Field(foreign_key="sessions.id")
    speaker_id: uuid.UUID = Field(foreign_key="speakers.id")
    display_order: int = Field(default=0)


class SessionSpeaker(Base, SessionSpeakerBase, table=True):
    __tablename__ = "session_speakers"
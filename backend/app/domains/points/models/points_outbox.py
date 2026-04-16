import datetime
import uuid

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.utils.models.base import Base


class PointsOutboxBase(SQLModel):
    event_type: str = Field(max_length=64)
    participant_id: uuid.UUID = Field(foreign_key="participants.id", index=True)
    delta: int
    resulting_balance: int
    last_activity_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    attempts: int = Field(default=0)
    next_attempt_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    sent_at: datetime.datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    last_error: str | None = Field(default=None, max_length=1000)


class PointsOutbox(Base, PointsOutboxBase, table=True):
    __tablename__ = "points_outbox"

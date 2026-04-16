import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


class ParticipantPoints(SQLModel, table=True):
    __tablename__ = "participant_points"

    participant_id: uuid.UUID = Field(
        foreign_key="participants.id",
        primary_key=True,
    )
    total_points: int = Field(default=0)
    last_activity_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )

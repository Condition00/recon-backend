import uuid
from datetime import datetime

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.utils.models.base import Base


class ZoneRegistrationBase(SQLModel):
    participant_id: uuid.UUID = Field(foreign_key="participants.id", index=True)
    zone_id: uuid.UUID = Field(foreign_key="zones.id", index=True)
    pass_code: str = Field(max_length=64, unique=True, index=True)
    is_active: bool = Field(default=True, index=True)
    checked_in_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    checked_in_by: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)


class ZoneRegistration(Base, ZoneRegistrationBase, table=True):
    __tablename__ = "zone_registrations"
    __table_args__ = (
        UniqueConstraint("participant_id", "zone_id", name="uq_zone_registrations_participant_zone"),
    )

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.utils.models.base import Base


class PointLedgerEntryBase(SQLModel):
    amount: int = Field()
    reason: str = Field(max_length=200)


class PointLedgerEntry(Base, PointLedgerEntryBase, table=True):
    __tablename__ = "point_ledger"

    participant_id: uuid.UUID = Field(foreign_key="participants.id", index=True)
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )

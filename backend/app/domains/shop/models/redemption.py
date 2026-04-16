import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.utils.models.base import Base


class RedemptionBase(SQLModel):
    fulfillment_notes: Optional[str] = Field(default=None, max_length=500)


class Redemption(Base, RedemptionBase, table=True):
    __tablename__ = "redemptions"

    participant_id: uuid.UUID = Field(foreign_key="participants.id", index=True)
    item_id: uuid.UUID = Field(foreign_key="shop_items.id", index=True)
    redeemed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
    fulfilled_at: Optional[datetime] = Field(default=None, sa_type=DateTime(timezone=True))

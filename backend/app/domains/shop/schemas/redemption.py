import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel


class RedemptionRead(SQLModel):
    id: uuid.UUID
    participant_id: uuid.UUID
    item_id: uuid.UUID
    item_name: str
    point_cost: int
    redeemed_at: datetime
    fulfilled_at: Optional[datetime]
    fulfillment_notes: Optional[str]
    created_at: datetime


class RedemptionFulfill(SQLModel):
    fulfillment_notes: Optional[str] = None

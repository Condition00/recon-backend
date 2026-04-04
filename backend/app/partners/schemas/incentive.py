import uuid
from decimal import Decimal
from typing import Optional

from sqlmodel import SQLModel

from app.partners.models.incentive import IncentiveType


class PartnerIncentiveCreate(SQLModel):
    title: str
    incentive_type: IncentiveType
    monetary_value: Optional[Decimal] = None
    description: Optional[str] = None
    display_order: int = 0


class PartnerIncentiveRead(SQLModel):
    id: uuid.UUID
    title: str
    incentive_type: IncentiveType
    monetary_value: Optional[Decimal]
    description: Optional[str]
    display_order: int


class PartnerIncentiveUpdate(SQLModel):
    title: Optional[str] = None
    incentive_type: Optional[IncentiveType] = None
    monetary_value: Optional[Decimal] = None
    description: Optional[str] = None
    display_order: Optional[int] = None

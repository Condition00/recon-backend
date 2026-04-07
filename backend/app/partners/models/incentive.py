import uuid
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.utils.models.base import Base


class IncentiveType(str, Enum):
    monetary = "monetary"
    in_kind = "in_kind"


class PartnerIncentiveBase(SQLModel):
    title: str = Field(max_length=300)
    incentive_type: IncentiveType
    monetary_value: Optional[Decimal] = Field(default=None, decimal_places=2, max_digits=12)
    description: Optional[str] = Field(default=None, max_length=2000)
    display_order: int = Field(default=0)


class PartnerIncentive(Base, PartnerIncentiveBase, table=True):
    __tablename__ = "partner_incentives"

    partner_id: uuid.UUID = Field(foreign_key="partners.id", index=True)

    partner: Optional["Partner"] = Relationship(back_populates="incentives")


from app.partners.models.partner import Partner  # noqa: E402, F401

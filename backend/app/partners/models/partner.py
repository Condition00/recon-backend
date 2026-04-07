import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.utils.models.base import Base


class SponsorshipType(str, Enum):
    monetary = "monetary"
    in_kind = "in_kind"
    hybrid = "hybrid"


class PartnerStatus(str, Enum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"


class PartnerBase(SQLModel):
    company_name: str = Field(max_length=200)
    company_website: Optional[str] = Field(default=None, max_length=500)
    contact_name: str = Field(max_length=200)
    contact_email: str = Field(max_length=320)
    sponsorship_type: SponsorshipType
    offering_writeup: str = Field(max_length=5000)


class Partner(Base, PartnerBase, table=True):
    __tablename__ = "partners"

    user_id: uuid.UUID = Field(foreign_key="users.id", unique=True, index=True)

    status: PartnerStatus = Field(default=PartnerStatus.pending_review)
    reviewed_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    reviewed_at: Optional[datetime] = Field(default=None)
    review_notes: Optional[str] = Field(default=None, max_length=1000)

    incentives: list["PartnerIncentive"] = Relationship(
        back_populates="partner",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "PartnerIncentive.display_order"},
    )
    assets: list["PartnerAsset"] = Relationship(
        back_populates="partner",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    reports: list["PartnerReport"] = Relationship(
        back_populates="partner",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


from app.partners.models.incentive import PartnerIncentive  # noqa: E402, F401
from app.partners.models.asset import PartnerAsset  # noqa: E402, F401
from app.partners.models.report import PartnerReport  # noqa: E402, F401

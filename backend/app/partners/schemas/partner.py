import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel

from app.partners.models.partner import PartnerStatus, SponsorshipType
from app.partners.schemas.incentive import PartnerIncentiveCreate, PartnerIncentiveRead
from app.partners.schemas.asset import PartnerAssetRead


class PartnerCreate(SQLModel):
    company_name: str
    company_website: Optional[str] = None
    contact_name: str
    contact_email: str
    sponsorship_type: SponsorshipType
    offering_writeup: str
    incentives: list[PartnerIncentiveCreate] = []


class PartnerRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    company_name: str
    company_website: Optional[str]
    contact_name: str
    contact_email: str
    sponsorship_type: SponsorshipType
    offering_writeup: str
    status: PartnerStatus
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]
    created_at: datetime
    incentives: list[PartnerIncentiveRead] = []
    assets: list[PartnerAssetRead] = []


class PartnerStatusUpdate(SQLModel):
    status: PartnerStatus
    review_notes: Optional[str] = None

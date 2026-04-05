import uuid
from typing import Optional

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.partners.models.partner import Partner, PartnerStatus
from app.partners.schemas.partner import PartnerCreate


def _partner_query():
    return select(Partner).options(
        selectinload(Partner.incentives),
        selectinload(Partner.assets),
    )


async def get_partner_by_id(db: AsyncSession, partner_id: uuid.UUID) -> Optional[Partner]:
    result = await db.exec(_partner_query().where(Partner.id == partner_id))
    return result.one_or_none()


async def get_partner_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[Partner]:
    result = await db.exec(_partner_query().where(Partner.user_id == user_id))
    return result.one_or_none()


async def list_partners(
    db: AsyncSession, *, status: Optional[PartnerStatus] = None, skip: int = 0, limit: int = 50
) -> list[Partner]:
    q = _partner_query()
    if status:
        q = q.where(Partner.status == status)
    q = q.offset(skip).limit(limit).order_by(Partner.created_at.desc())
    result = await db.exec(q)
    return list(result.all())


async def create_partner(db: AsyncSession, *, user_id: uuid.UUID, payload: PartnerCreate) -> Partner:
    partner = Partner(
        user_id=user_id,
        company_name=payload.company_name,
        company_website=payload.company_website,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        sponsorship_type=payload.sponsorship_type,
        offering_writeup=payload.offering_writeup,
    )
    db.add(partner)
    await db.flush()
    return partner


async def update_partner_status(
    db: AsyncSession,
    partner: Partner,
    *,
    status: PartnerStatus,
    reviewed_by: uuid.UUID,
    review_notes: Optional[str] = None,
) -> Partner:
    from datetime import datetime, timezone
    partner.status = status
    partner.reviewed_by = reviewed_by
    partner.reviewed_at = datetime.now(timezone.utc)
    partner.review_notes = review_notes
    await db.flush()
    return partner

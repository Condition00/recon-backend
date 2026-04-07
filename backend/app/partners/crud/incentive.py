import uuid
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.partners.models.incentive import PartnerIncentive
from app.partners.schemas.incentive import PartnerIncentiveCreate, PartnerIncentiveUpdate


async def list_incentives(db: AsyncSession, *, partner_id: uuid.UUID) -> list[PartnerIncentive]:
    result = await db.exec(
        select(PartnerIncentive)
        .where(PartnerIncentive.partner_id == partner_id)
        .order_by(PartnerIncentive.display_order)
    )
    return list(result.all())


async def create_incentive(
    db: AsyncSession, *, partner_id: uuid.UUID, payload: PartnerIncentiveCreate
) -> PartnerIncentive:
    incentive = PartnerIncentive(partner_id=partner_id, **payload.model_dump())
    db.add(incentive)
    await db.flush()
    return incentive


async def get_incentive_by_id(
    db: AsyncSession, incentive_id: uuid.UUID
) -> Optional[PartnerIncentive]:
    return await db.get(PartnerIncentive, incentive_id)


async def update_incentive(
    db: AsyncSession, incentive: PartnerIncentive, payload: PartnerIncentiveUpdate
) -> PartnerIncentive:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(incentive, field, value)
    await db.flush()
    return incentive


async def delete_incentive(db: AsyncSession, incentive: PartnerIncentive) -> None:
    await db.delete(incentive)
    await db.flush()

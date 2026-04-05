import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import User
from app.partners.models.partner import Partner, PartnerStatus
from app.partners.models.incentive import PartnerIncentive
from app.partners.models.asset import PartnerAsset
from app.partners.schemas.asset import PartnerAssetCreate
from app.partners.schemas.incentive import PartnerIncentiveCreate, PartnerIncentiveUpdate
from app.partners.schemas.partner import PartnerCreate, PartnerStatusUpdate
from app.partners.service import (
    add_asset, add_incentive, edit_incentive, get_my_partner_profile,
    get_partner_or_404, list_all_partners, remove_asset, remove_incentive,
    review_partner_application, submit_partner_application,
)


async def apply(db: AsyncSession, user: User, payload: PartnerCreate) -> Partner:
    return await submit_partner_application(db, user=user, payload=payload)


async def my_profile(db: AsyncSession, user: User) -> Partner:
    return await get_my_partner_profile(db, user=user)


async def get_partner(db: AsyncSession, partner_id: uuid.UUID) -> Partner:
    return await get_partner_or_404(db, partner_id)


async def list_partners(
    db: AsyncSession, status: PartnerStatus | None, skip: int, limit: int
) -> list[Partner]:
    return await list_all_partners(db, status=status, skip=skip, limit=limit)


async def review(
    db: AsyncSession, partner_id: uuid.UUID, payload: PartnerStatusUpdate, admin: User
) -> Partner:
    return await review_partner_application(db, partner_id=partner_id, payload=payload, reviewed_by=admin.id)


async def create_incentive(
    db: AsyncSession, user: User, payload: PartnerIncentiveCreate
) -> PartnerIncentive:
    return await add_incentive(db, user=user, payload=payload)


async def update_incentive(
    db: AsyncSession, user: User, incentive_id: uuid.UUID, payload: PartnerIncentiveUpdate
) -> PartnerIncentive:
    return await edit_incentive(db, user=user, incentive_id=incentive_id, payload=payload)


async def delete_incentive(db: AsyncSession, user: User, incentive_id: uuid.UUID) -> None:
    await remove_incentive(db, user=user, incentive_id=incentive_id)


async def upload_asset(db: AsyncSession, user: User, payload: PartnerAssetCreate) -> PartnerAsset:
    return await add_asset(db, user=user, payload=payload)


async def delete_asset(db: AsyncSession, user: User, asset_id: uuid.UUID) -> None:
    await remove_asset(db, user=user, asset_id=asset_id)

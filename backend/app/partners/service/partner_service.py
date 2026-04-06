import uuid

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import ROLE_PARTNER, User
from app.domains.auth.crud import get_role_by_name
from app.partners.crud import (
    create_asset, create_incentive, create_partner, delete_asset,
    delete_incentive, get_asset_by_id, get_incentive_by_id,
    get_partner_by_id, get_partner_by_user_id, list_partners,
    update_partner_status,
)
from app.partners.models.partner import Partner, PartnerStatus
from app.partners.schemas.asset import PartnerAssetCreate
from app.partners.schemas.incentive import PartnerIncentiveCreate, PartnerIncentiveUpdate
from app.partners.schemas.partner import PartnerCreate, PartnerStatusUpdate


async def submit_partner_application(
    db: AsyncSession, *, user: User, payload: PartnerCreate
) -> Partner:
    existing = await get_partner_by_user_id(db, user.id)
    if existing:
        raise HTTPException(status_code=409, detail="A partner application already exists for this account")

    partner = await create_partner(db, user_id=user.id, payload=payload)

    for incentive_payload in payload.incentives:
        await create_incentive(db, partner_id=partner.id, payload=incentive_payload)

    hydrated_partner = await get_partner_by_id(db, partner.id)
    if not hydrated_partner:
        raise HTTPException(status_code=500, detail="Failed to load created partner application")
    return hydrated_partner


async def get_my_partner_profile(db: AsyncSession, *, user: User) -> Partner:
    partner = await get_partner_by_user_id(db, user.id)
    if not partner:
        raise HTTPException(status_code=404, detail="No partner application found")
    return partner


async def get_partner_or_404(db: AsyncSession, partner_id: uuid.UUID) -> Partner:
    partner = await get_partner_by_id(db, partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    return partner


async def list_all_partners(
    db: AsyncSession, *, status: PartnerStatus | None = None, skip: int = 0, limit: int = 50
) -> list[Partner]:
    return await list_partners(db, status=status, skip=skip, limit=limit)


async def review_partner_application(
    db: AsyncSession, *, partner_id: uuid.UUID, payload: PartnerStatusUpdate, reviewed_by: uuid.UUID
) -> Partner:
    partner = await get_partner_or_404(db, partner_id)
    if partner.status != PartnerStatus.pending_review:
        raise HTTPException(status_code=409, detail="Application has already been reviewed")

    partner = await update_partner_status(
        db, partner, status=payload.status,
        reviewed_by=reviewed_by, review_notes=payload.review_notes,
    )

    if payload.status == PartnerStatus.approved:
        await _assign_partner_role(db, partner.user_id)

    hydrated_partner = await get_partner_by_id(db, partner.id)
    if not hydrated_partner:
        raise HTTPException(status_code=500, detail="Failed to load reviewed partner application")
    return hydrated_partner


async def _assign_partner_role(db: AsyncSession, user_id: uuid.UUID) -> None:
    from app.domains.auth.crud import get_user_by_id
    user = await get_user_by_id(db, user_id)
    if not user:
        return
    role = await get_role_by_name(db, ROLE_PARTNER)
    if role:
        user.role_id = role.id
        await db.flush()


async def add_incentive(
    db: AsyncSession, *, user: User, payload: PartnerIncentiveCreate
) -> "PartnerIncentive":
    from app.partners.models.incentive import PartnerIncentive
    partner = await get_my_partner_profile(db, user=user)
    return await create_incentive(db, partner_id=partner.id, payload=payload)


async def edit_incentive(
    db: AsyncSession, *, user: User, incentive_id: uuid.UUID, payload: PartnerIncentiveUpdate
) -> "PartnerIncentive":
    incentive = await get_incentive_by_id(db, incentive_id)
    if not incentive:
        raise HTTPException(status_code=404, detail="Incentive not found")
    partner = await get_my_partner_profile(db, user=user)
    if incentive.partner_id != partner.id:
        raise HTTPException(status_code=403, detail="Not your incentive")
    return await update_incentive(db, incentive, payload)


async def remove_incentive(db: AsyncSession, *, user: User, incentive_id: uuid.UUID) -> None:
    incentive = await get_incentive_by_id(db, incentive_id)
    if not incentive:
        raise HTTPException(status_code=404, detail="Incentive not found")
    partner = await get_my_partner_profile(db, user=user)
    if incentive.partner_id != partner.id:
        raise HTTPException(status_code=403, detail="Not your incentive")
    await delete_incentive(db, incentive)


async def add_asset(
    db: AsyncSession, *, user: User, payload: PartnerAssetCreate
) -> "PartnerAsset":
    from app.partners.models.asset import PartnerAsset
    partner = await get_my_partner_profile(db, user=user)
    if partner.status != PartnerStatus.approved:
        raise HTTPException(status_code=403, detail="Asset uploads are only available after application approval")
    return await create_asset(db, partner_id=partner.id, uploaded_by=user.id, payload=payload)


async def remove_asset(db: AsyncSession, *, user: User, asset_id: uuid.UUID) -> None:
    asset = await get_asset_by_id(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    partner = await get_my_partner_profile(db, user=user)
    if asset.partner_id != partner.id:
        raise HTTPException(status_code=403, detail="Not your asset")
    await delete_asset(db, asset)

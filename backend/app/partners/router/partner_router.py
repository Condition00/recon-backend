import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.database import get_db
from app.domains.auth.models import ROLE_ADMIN, ROLE_PARTNER, User
from app.partners.controller import (
    apply, create_incentive, delete_asset, delete_incentive,
    get_partner, list_partners, my_profile, review, update_incentive, upload_asset,
)
from app.partners.models.partner import PartnerStatus
from app.partners.schemas.asset import PartnerAssetCreate, PartnerAssetRead
from app.partners.schemas.incentive import PartnerIncentiveCreate, PartnerIncentiveRead, PartnerIncentiveUpdate
from app.partners.schemas.partner import PartnerCreate, PartnerRead, PartnerStatusUpdate
from app.utils.deps import get_current_user, require_roles

router = APIRouter(prefix="/partners", tags=["partners"])


# ── Partner application (any authenticated user) ──────────────────────────────

@router.post("/apply", response_model=PartnerRead, status_code=status.HTTP_201_CREATED)
async def apply_as_partner(
    payload: PartnerCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await apply(db, user, payload)


@router.get("/me", response_model=PartnerRead)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await my_profile(db, user)


# ── Incentives (partner only) ─────────────────────────────────────────────────

@router.post("/me/incentives", response_model=PartnerIncentiveRead, status_code=status.HTTP_201_CREATED)
async def add_incentive(
    payload: PartnerIncentiveCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(ROLE_PARTNER)),
):
    return await create_incentive(db, user, payload)


@router.patch("/me/incentives/{incentive_id}", response_model=PartnerIncentiveRead)
async def edit_incentive(
    incentive_id: uuid.UUID,
    payload: PartnerIncentiveUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(ROLE_PARTNER)),
):
    return await update_incentive(db, user, incentive_id, payload)


@router.delete("/me/incentives/{incentive_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_incentive(
    incentive_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(ROLE_PARTNER)),
):
    await delete_incentive(db, user, incentive_id)


# ── Assets (partner only, approved only) ─────────────────────────────────────

@router.post("/me/assets", response_model=PartnerAssetRead, status_code=status.HTTP_201_CREATED)
async def add_asset(
    payload: PartnerAssetCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(ROLE_PARTNER)),
):
    return await upload_asset(db, user, payload)


@router.delete("/me/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(ROLE_PARTNER)),
):
    await delete_asset(db, user, asset_id)


# ── Admin review ──────────────────────────────────────────────────────────────

@router.get("/", response_model=list[PartnerRead])
async def list_all_partners(
    status_filter: Optional[PartnerStatus] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(ROLE_ADMIN)),
):
    return await list_partners(db, status_filter, skip, limit)


@router.get("/{partner_id}", response_model=PartnerRead)
async def get_partner_by_id(
    partner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(ROLE_ADMIN)),
):
    return await get_partner(db, partner_id)


@router.post("/{partner_id}/review", response_model=PartnerRead)
async def review_application(
    partner_id: uuid.UUID,
    payload: PartnerStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(ROLE_ADMIN)),
):
    return await review(db, partner_id, payload, admin)

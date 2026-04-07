import uuid
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.partners.models.asset import PartnerAsset
from app.partners.schemas.asset import PartnerAssetCreate


async def list_assets(db: AsyncSession, *, partner_id: uuid.UUID) -> list[PartnerAsset]:
    result = await db.exec(
        select(PartnerAsset)
        .where(PartnerAsset.partner_id == partner_id)
        .order_by(PartnerAsset.created_at.desc())
    )
    return list(result.all())


async def create_asset(
    db: AsyncSession, *, partner_id: uuid.UUID, uploaded_by: uuid.UUID, payload: PartnerAssetCreate
) -> PartnerAsset:
    asset = PartnerAsset(partner_id=partner_id, uploaded_by=uploaded_by, **payload.model_dump())
    db.add(asset)
    await db.flush()
    return asset


async def get_asset_by_id(db: AsyncSession, asset_id: uuid.UUID) -> Optional[PartnerAsset]:
    return await db.get(PartnerAsset, asset_id)


async def delete_asset(db: AsyncSession, asset: PartnerAsset) -> None:
    await db.delete(asset)
    await db.flush()

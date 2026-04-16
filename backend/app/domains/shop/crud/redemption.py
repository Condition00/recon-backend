import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.shop.models import Redemption


async def create_redemption(
    db: AsyncSession, *, participant_id: uuid.UUID, item_id: uuid.UUID
) -> Redemption:
    redemption = Redemption(
        participant_id=participant_id,
        item_id=item_id,
    )
    db.add(redemption)
    await db.flush()
    await db.refresh(redemption)
    return redemption


async def get_redemption_by_id(db: AsyncSession, redemption_id: uuid.UUID) -> Redemption | None:
    return await db.get(Redemption, redemption_id)


async def list_redemptions_by_participant(
    db: AsyncSession, participant_id: uuid.UUID
) -> list[Redemption]:
    query = (
        select(Redemption)
        .where(Redemption.participant_id == participant_id)
        .order_by(Redemption.redeemed_at.desc())
    )
    result = await db.exec(query)
    return list(result.all())


async def list_all_redemptions(
    db: AsyncSession, *, fulfilled: Optional[bool] = None
) -> list[Redemption]:
    query = select(Redemption).order_by(Redemption.redeemed_at.desc())
    if fulfilled is True:
        query = query.where(Redemption.fulfilled_at.is_not(None))
    elif fulfilled is False:
        query = query.where(Redemption.fulfilled_at.is_(None))
    result = await db.exec(query)
    return list(result.all())


async def fulfill_redemption(
    db: AsyncSession, redemption: Redemption, *, notes: Optional[str] = None
) -> Redemption:
    redemption.fulfilled_at = datetime.now(timezone.utc)
    if notes is not None:
        redemption.fulfillment_notes = notes
    await db.flush()
    await db.refresh(redemption)
    return redemption

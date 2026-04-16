import uuid
from typing import Optional

from redis.asyncio import Redis
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import User
from app.domains.shop.schemas import (
    RedemptionFulfill,
    RedemptionRedeem,
    RedemptionRead,
    ShopItemCreate,
    ShopItemRead,
    ShopItemUpdate,
)
from app.domains.shop.service import (
    create_shop_item,
    fulfill_redemption_admin,
    get_shop_item_or_404,
    list_all_redemptions_admin,
    list_my_redemptions,
    list_shop_items,
    redeem_item,
    update_shop_item,
)


# ---------------------------------------------------------------------------
# Catalogue (participant-facing)
# ---------------------------------------------------------------------------

async def list_items(db: AsyncSession) -> list[ShopItemRead]:
    return await list_shop_items(db)


async def get_item(db: AsyncSession, item_id: uuid.UUID) -> ShopItemRead:
    return await get_shop_item_or_404(db, item_id)


async def redeem(
    db: AsyncSession,
    *,
    item_id: uuid.UUID,
    participant_id: uuid.UUID,
    actor: User,
    payload: RedemptionRedeem,
    redis: Redis | None,
) -> RedemptionRead:
    return await redeem_item(
        db,
        item_id=item_id,
        participant_id=participant_id,
        actor=actor,
        payload=payload,
        redis=redis,
    )


async def my_redemptions(
    db: AsyncSession, participant_id: uuid.UUID
) -> list[RedemptionRead]:
    return await list_my_redemptions(db, participant_id)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

async def admin_create_item(db: AsyncSession, payload: ShopItemCreate) -> ShopItemRead:
    return await create_shop_item(db, payload)


async def admin_update_item(
    db: AsyncSession, item_id: uuid.UUID, payload: ShopItemUpdate
) -> ShopItemRead:
    return await update_shop_item(db, item_id, payload)


async def admin_list_redemptions(
    db: AsyncSession, *, fulfilled: Optional[bool] = None
) -> list[RedemptionRead]:
    return await list_all_redemptions_admin(db, fulfilled=fulfilled)


async def admin_fulfill_redemption(
    db: AsyncSession, redemption_id: uuid.UUID, payload: RedemptionFulfill
) -> RedemptionRead:
    return await fulfill_redemption_admin(db, redemption_id, payload)

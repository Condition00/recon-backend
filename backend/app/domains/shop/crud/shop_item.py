import uuid
import warnings

from sqlalchemy import func
from sqlalchemy import select as sa_select
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.shop.models import Redemption, ShopItem
from app.domains.shop.schemas import ShopItemCreate, ShopItemUpdate


async def list_active_items(db: AsyncSession) -> list[ShopItem]:
    query = (
        select(ShopItem)
        .where(ShopItem.is_active.is_(True))
        .order_by(ShopItem.created_at.desc())
    )
    result = await db.exec(query)
    return list(result.all())


async def get_item_by_id(db: AsyncSession, item_id: uuid.UUID) -> ShopItem | None:
    return await db.get(ShopItem, item_id)


async def get_item_for_update(db: AsyncSession, item_id: uuid.UUID) -> ShopItem | None:
    """Acquire a row-level lock on the item for concurrent stock safety.

    Falls back to a plain SELECT on dialects that do not support FOR UPDATE (e.g. SQLite in tests).
    """
    query = select(ShopItem).where(ShopItem.id == item_id)
    bind = db.get_bind()
    if bind.dialect.name != "sqlite":
        query = query.with_for_update()
    result = await db.exec(query)
    return result.one_or_none()


async def create_item(db: AsyncSession, *, payload: ShopItemCreate) -> ShopItem:
    item = ShopItem(
        name=payload.name,
        description=payload.description,
        point_cost=payload.point_cost,
        stock=payload.stock,
        photo_key=payload.photo_key,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def update_item(db: AsyncSession, item: ShopItem, payload: ShopItemUpdate) -> ShopItem:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)
    await db.flush()
    await db.refresh(item)
    return item


async def count_redemptions_for_item(db: AsyncSession, item_id: uuid.UUID) -> int:
    query = sa_select(func.count()).where(Redemption.item_id == item_id)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        result = await db.execute(query)
    return result.scalar_one()

import hashlib
import uuid
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import User
from app.domains.points import crud as points_crud
from app.domains.points.models import PointLedgerEntry
from app.domains.points.schemas import PointAwardCreate
from app.domains.points.service import award_points
from app.domains.shop.crud import (
    count_redemptions_for_item,
    create_item,
    create_redemption,
    fulfill_redemption as crud_fulfill_redemption,
    get_item_by_id,
    get_item_for_update,
    get_redemption_by_id,
    get_redemption_by_idempotency_key,
    list_active_items,
    list_all_redemptions as crud_list_all_redemptions,
    list_redemptions_by_participant,
    update_item,
)
from app.domains.shop.models import Redemption, ShopItem
from app.domains.shop.schemas import (
    RedemptionFulfill,
    RedemptionRedeem,
    RedemptionRead,
    ShopItemCreate,
    ShopItemRead,
    ShopItemUpdate,
)


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------

async def list_shop_items(db: AsyncSession) -> list[ShopItemRead]:
    """Return all active shop items with computed remaining_stock."""
    items = await list_active_items(db)
    result = []
    for item in items:
        remaining = None
        if item.stock is not None:
            redeemed = await count_redemptions_for_item(db, item.id)
            remaining = max(item.stock - redeemed, 0)
        result.append(_item_to_read(item, remaining))
    return result


async def get_shop_item_or_404(db: AsyncSession, item_id: uuid.UUID) -> ShopItemRead:
    """Return a single shop item or raise 404."""
    item = await get_item_by_id(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Shop item not found")
    remaining = None
    if item.stock is not None:
        redeemed = await count_redemptions_for_item(db, item.id)
        remaining = max(item.stock - redeemed, 0)
    return _item_to_read(item, remaining)


# ---------------------------------------------------------------------------
# Admin item management
# ---------------------------------------------------------------------------

async def create_shop_item(db: AsyncSession, payload: ShopItemCreate) -> ShopItemRead:
    item = await create_item(db, payload=payload)
    remaining = item.stock  # no redemptions yet
    return _item_to_read(item, remaining)


async def update_shop_item(
    db: AsyncSession, item_id: uuid.UUID, payload: ShopItemUpdate
) -> ShopItemRead:
    item = await get_item_by_id(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Shop item not found")
    item = await update_item(db, item, payload)
    remaining = None
    if item.stock is not None:
        redeemed = await count_redemptions_for_item(db, item.id)
        remaining = max(item.stock - redeemed, 0)
    return _item_to_read(item, remaining)


# ---------------------------------------------------------------------------
# Redemption
# ---------------------------------------------------------------------------

async def redeem_item(
    db: AsyncSession,
    *,
    item_id: uuid.UUID,
    participant_id: uuid.UUID,
    actor: User,
    payload: RedemptionRedeem,
) -> RedemptionRead:
    """
    Atomic redeem: row-lock item → check active → check stock → check balance → deduct → create redemption.

    Everything runs inside the caller's transaction so commit/rollback is automatic.
    """
    existing = await get_redemption_by_idempotency_key(
        db, idempotency_key=payload.idempotency_key
    )
    if existing is not None:
        if existing.participant_id != participant_id or existing.item_id != item_id:
            raise HTTPException(
                status_code=409,
                detail="idempotency_key already exists for a different redemption request",
            )
        return await _enrich_redemption(db, existing)

    # 1. Lock the item row
    item = await get_item_for_update(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Shop item not found")
    if not item.is_active:
        raise HTTPException(status_code=400, detail="Item is not available for redemption")

    # 2. Stock check
    if item.stock is not None:
        redeemed_count = await count_redemptions_for_item(db, item.id)
        if redeemed_count >= item.stock:
            raise HTTPException(status_code=409, detail="Item is out of stock")

    # 3. Balance check
    balance = await _get_participant_balance(db, participant_id)
    if balance < item.point_cost:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient points. Balance: {balance}, cost: {item.point_cost}",
        )

    # 4. Deduct points
    await _spend_points(
        db,
        participant_id=participant_id,
        amount=item.point_cost,
        reason=_build_shop_redeem_reason(item.name),
        reference_id=item.id,
        actor=actor,
        idempotency_key=_build_redeem_points_idempotency_key(
            participant_id=participant_id,
            item_id=item.id,
            request_idempotency_key=payload.idempotency_key,
        ),
        note=f"shop redemption for {item.name}",
    )

    # 5. Create redemption record
    try:
        async with db.begin_nested():
            redemption = await create_redemption(
                db,
                participant_id=participant_id,
                item_id=item.id,
                idempotency_key=payload.idempotency_key,
            )
    except IntegrityError:
        existing = await get_redemption_by_idempotency_key(
            db, idempotency_key=payload.idempotency_key
        )
        if existing is None:
            raise
        if existing.participant_id != participant_id or existing.item_id != item.id:
            raise HTTPException(
                status_code=409,
                detail="idempotency_key already exists for a different redemption request",
            )
        return await _enrich_redemption(db, existing)

    return _redemption_to_read(redemption, item)


# ---------------------------------------------------------------------------
# Redemption queries
# ---------------------------------------------------------------------------

async def list_my_redemptions(
    db: AsyncSession, participant_id: uuid.UUID
) -> list[RedemptionRead]:
    redemptions = await list_redemptions_by_participant(db, participant_id)
    return [await _enrich_redemption(db, r) for r in redemptions]


async def list_all_redemptions_admin(
    db: AsyncSession, *, fulfilled: Optional[bool] = None
) -> list[RedemptionRead]:
    redemptions = await crud_list_all_redemptions(db, fulfilled=fulfilled)
    return [await _enrich_redemption(db, r) for r in redemptions]


async def fulfill_redemption_admin(
    db: AsyncSession, redemption_id: uuid.UUID, payload: RedemptionFulfill
) -> RedemptionRead:
    redemption = await get_redemption_by_id(db, redemption_id)
    if not redemption:
        raise HTTPException(status_code=404, detail="Redemption not found")
    if redemption.fulfilled_at is not None:
        raise HTTPException(status_code=409, detail="Redemption is already fulfilled")
    redemption = await crud_fulfill_redemption(db, redemption, notes=payload.fulfillment_notes)
    return await _enrich_redemption(db, redemption)


# ---------------------------------------------------------------------------
# Points helpers (stop-gap until points domain is built)
# ---------------------------------------------------------------------------

async def _get_participant_balance(db: AsyncSession, participant_id: uuid.UUID) -> int:
    """Read participant balance from points projection."""
    return await points_crud.get_balance_for_participant(db, participant_id=participant_id)


async def _spend_points(
    db: AsyncSession,
    *,
    participant_id: uuid.UUID,
    amount: int,
    reason: str,
    reference_id: uuid.UUID | None,
    actor: User,
    idempotency_key: str,
    note: str | None = None,
) -> PointLedgerEntry:
    """Spend points through the points domain service to preserve invariants."""
    payload = PointAwardCreate(
        participant_id=participant_id,
        amount=-amount,
        reason=reason,
        reference_id=reference_id,
        idempotency_key=idempotency_key,
        note=note,
    )
    entry, _ = await award_points(db, payload=payload, actor=actor)
    return entry


def _build_shop_redeem_reason(item_name: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in item_name).strip("_")
    if not normalized:
        normalized = "item"
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    if not normalized[0].isalpha():
        normalized = f"item_{normalized}"
    return f"shop.redeem.{normalized}"


def _build_redeem_points_idempotency_key(
    *, participant_id: uuid.UUID, item_id: uuid.UUID, request_idempotency_key: str
) -> str:
    raw = f"{participant_id}:{item_id}:{request_idempotency_key}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return f"shop.redeem.{digest[:87]}"


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------

def _item_to_read(item: ShopItem, remaining_stock: Optional[int]) -> ShopItemRead:
    return ShopItemRead(
        id=item.id,
        name=item.name,
        description=item.description,
        point_cost=item.point_cost,
        stock=item.stock,
        remaining_stock=remaining_stock,
        is_active=item.is_active,
        photo_key=item.photo_key,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _redemption_to_read(redemption: Redemption, item: ShopItem) -> RedemptionRead:
    return RedemptionRead(
        id=redemption.id,
        participant_id=redemption.participant_id,
        item_id=redemption.item_id,
        item_name=item.name,
        point_cost=item.point_cost,
        redeemed_at=redemption.redeemed_at,
        fulfilled_at=redemption.fulfilled_at,
        fulfillment_notes=redemption.fulfillment_notes,
        created_at=redemption.created_at,
    )


async def _enrich_redemption(db: AsyncSession, redemption: Redemption) -> RedemptionRead:
    """Load the item to denormalize name/cost into the read schema."""
    item = await get_item_by_id(db, redemption.item_id)
    name = item.name if item else "[deleted]"
    cost = item.point_cost if item else 0
    return RedemptionRead(
        id=redemption.id,
        participant_id=redemption.participant_id,
        item_id=redemption.item_id,
        item_name=name,
        point_cost=cost,
        redeemed_at=redemption.redeemed_at,
        fulfilled_at=redemption.fulfilled_at,
        fulfillment_notes=redemption.fulfillment_notes,
        created_at=redemption.created_at,
    )

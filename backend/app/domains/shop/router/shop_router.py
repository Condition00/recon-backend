import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.database import get_db
from app.domains.auth.models import ROLE_ADMIN, User
from app.domains.participants.crud import get_participant_by_user_id
from app.domains.shop.controller import (
    admin_create_item,
    admin_fulfill_redemption,
    admin_list_redemptions,
    admin_update_item,
    get_item,
    list_items,
    my_redemptions,
    redeem,
)
from app.domains.shop.schemas import (
    RedemptionFulfill,
    RedemptionRedeem,
    RedemptionRead,
    ShopItemCreate,
    ShopItemRead,
    ShopItemUpdate,
)
from app.utils.deps import get_current_user, require_roles

router = APIRouter(prefix="/shop", tags=["shop"])


# ---------------------------------------------------------------------------
# Participant-facing
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[ShopItemRead])
async def list_shop_items_route(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List all active shop items with remaining stock."""
    return await list_items(db)


# NOTE: static paths BEFORE /{item_id} to avoid path conflicts
@router.get("/me/redemptions", response_model=list[RedemptionRead])
async def my_redemptions_route(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the current participant's redemption history."""
    participant = await _require_participant(db, user)
    return await my_redemptions(db, participant.id)


@router.get("/redemptions", response_model=list[RedemptionRead])
async def admin_list_redemptions_route(
    fulfilled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(ROLE_ADMIN)),
):
    """Admin: list all redemptions, optionally filtered by fulfillment state."""
    return await admin_list_redemptions(db, fulfilled=fulfilled)


@router.patch("/redemptions/{redemption_id}/fulfill", response_model=RedemptionRead)
async def admin_fulfill_redemption_route(
    redemption_id: uuid.UUID,
    payload: RedemptionFulfill,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(ROLE_ADMIN)),
):
    """Admin: mark a redemption as fulfilled (merch handed over)."""
    return await admin_fulfill_redemption(db, redemption_id, payload)


@router.get("/{item_id}", response_model=ShopItemRead)
async def get_shop_item_route(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get a single shop item by ID."""
    return await get_item(db, item_id)


@router.post("/{item_id}/redeem", response_model=RedemptionRead)
async def redeem_item_route(
    item_id: uuid.UUID,
    payload: RedemptionRedeem,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Redeem a shop item: checks balance, deducts points, decrements stock."""
    participant = await _require_participant(db, user)
    return await redeem(
        db,
        item_id=item_id,
        participant_id=participant.id,
        actor=user,
        payload=payload,
    )


# ---------------------------------------------------------------------------
# Admin item management
# ---------------------------------------------------------------------------

@router.post("/", response_model=ShopItemRead, status_code=status.HTTP_201_CREATED)
async def create_shop_item_route(
    payload: ShopItemCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(ROLE_ADMIN)),
):
    """Admin: create a new shop item."""
    return await admin_create_item(db, payload)


@router.patch("/{item_id}", response_model=ShopItemRead)
async def update_shop_item_route(
    item_id: uuid.UUID,
    payload: ShopItemUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(ROLE_ADMIN)),
):
    """Admin: update a shop item (name, price, stock, active toggle)."""
    return await admin_update_item(db, item_id, payload)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _require_participant(db: AsyncSession, user: User):
    """Look up the Participant row for the current user, or 404."""
    from fastapi import HTTPException

    participant = await get_participant_by_user_id(db, user.id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant profile not found. Create a profile first.")
    return participant

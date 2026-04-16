import datetime
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.database import get_db
from app.domains.auth.models import ROLE_ADMIN, User
from app.domains.points import controller
from app.domains.points.schemas import (
    PointAwardCreate,
    PointAwardRead,
    PointLeaderboardMeRead,
    PointLeaderboardPageRead,
    PointMeRead,
    PointTransactionsPageRead,
)
from app.utils.deps import get_current_user, require_roles

router = APIRouter(prefix="/points", tags=["points"])


@router.post("/award", response_model=PointAwardRead, status_code=status.HTTP_201_CREATED)
async def award_points(
    payload: PointAwardCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(ROLE_ADMIN)),
):
    return await controller.award(db, payload=payload, actor=actor)


@router.get("/me", response_model=PointMeRead)
async def get_my_points(
    recent_limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await controller.me(db, user=user, recent_limit=recent_limit)


@router.get("/leaderboard", response_model=PointLeaderboardPageRead)
async def get_leaderboard(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await controller.leaderboard(db, skip=skip, limit=limit)


@router.get("/leaderboard/me", response_model=PointLeaderboardMeRead)
async def get_my_leaderboard_rank(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await controller.leaderboard_me(db, user=user)


@router.get("/transactions", response_model=PointTransactionsPageRead)
async def list_transactions(
    participant_id: uuid.UUID | None = None,
    reason: str | None = None,
    min_amount: int | None = None,
    max_amount: int | None = None,
    start_at: datetime.datetime | None = None,
    end_at: datetime.datetime | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(ROLE_ADMIN)),
):
    return await controller.transactions(
        db,
        participant_id=participant_id,
        reason=reason,
        min_amount=min_amount,
        max_amount=max_amount,
        start_at=start_at,
        end_at=end_at,
        skip=skip,
        limit=limit,
    )

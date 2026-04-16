import datetime
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import User
from app.domains.points.schemas import (
    PointAwardCreate,
    PointAwardRead,
    PointLeaderboardMeRead,
    PointLeaderboardPageRead,
    PointMeRead,
    PointTransactionsPageRead,
)
from app.domains.points.service import (
    award_points,
    get_leaderboard,
    get_my_points_summary,
    get_my_rank,
    get_transactions_for_admin,
    serialize_transaction,
)


async def award(
    db: AsyncSession,
    *,
    payload: PointAwardCreate,
    actor: User,
) -> PointAwardRead:
    tx, balance = await award_points(db, payload=payload, actor=actor)
    return PointAwardRead(transaction=serialize_transaction(tx), resulting_balance=balance)


async def me(db: AsyncSession, *, user: User, recent_limit: int) -> PointMeRead:
    return await get_my_points_summary(db, user=user, recent_limit=recent_limit)


async def leaderboard(db: AsyncSession, *, skip: int, limit: int) -> PointLeaderboardPageRead:
    return await get_leaderboard(db, skip=skip, limit=limit)


async def leaderboard_me(db: AsyncSession, *, user: User) -> PointLeaderboardMeRead:
    return await get_my_rank(db, user=user)


async def transactions(
    db: AsyncSession,
    *,
    participant_id: uuid.UUID | None,
    reason: str | None,
    min_amount: int | None,
    max_amount: int | None,
    start_at: datetime.datetime | None,
    end_at: datetime.datetime | None,
    skip: int,
    limit: int,
) -> PointTransactionsPageRead:
    return await get_transactions_for_admin(
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

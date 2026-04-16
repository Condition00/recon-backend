import datetime
import uuid

from redis.asyncio import Redis
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import User
from app.domains.points.schemas import (
    PointAwardCreate,
    PointAwardRead,
    PointCacheRebuildRead,
    PointLeaderboardMeRead,
    PointLeaderboardPageRead,
    PointMeRead,
    PointOutboxDrainRead,
    PointTransactionsPageRead,
)
from app.domains.points.service import (
    award_points,
    get_leaderboard,
    get_my_points_summary,
    get_my_rank,
    rebuild_leaderboard_cache,
    get_transactions_for_admin,
    serialize_transaction,
    drain_outbox_now,
)


async def award(
    db: AsyncSession,
    *,
    payload: PointAwardCreate,
    actor: User,
    redis: Redis | None,
) -> PointAwardRead:
    tx, balance = await award_points(db, payload=payload, actor=actor, redis=redis)
    return PointAwardRead(transaction=serialize_transaction(tx), resulting_balance=balance)


async def me(db: AsyncSession, *, user: User, recent_limit: int) -> PointMeRead:
    return await get_my_points_summary(db, user=user, recent_limit=recent_limit)


async def leaderboard(
    db: AsyncSession, *, skip: int, limit: int, redis: Redis | None
) -> PointLeaderboardPageRead:
    return await get_leaderboard(db, skip=skip, limit=limit, redis=redis)


async def leaderboard_me(
    db: AsyncSession, *, user: User, redis: Redis | None
) -> PointLeaderboardMeRead:
    return await get_my_rank(db, user=user, redis=redis)


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


async def rebuild_cache(
    db: AsyncSession,
    *,
    redis: Redis | None,
) -> PointCacheRebuildRead:
    total_ranked = await rebuild_leaderboard_cache(db, redis=redis)
    return PointCacheRebuildRead(total_ranked=total_ranked)


async def drain_outbox(
    db: AsyncSession,
    *,
    redis: Redis | None,
    limit: int,
) -> PointOutboxDrainRead:
    return await drain_outbox_now(db, redis=redis, limit=limit)

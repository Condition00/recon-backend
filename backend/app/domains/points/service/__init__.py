import datetime
import logging
import re
import uuid

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.post_commit import add_post_commit_hook
from app.domains.auth.models import User
from app.domains.participants.crud import get_participant_by_user_id
from app.domains.points import crud
from app.domains.points.models import PointLedger
from app.domains.points.schemas import (
    PointAwardCreate,
    PointLeaderboardEntry,
    PointLeaderboardMeRead,
    PointLeaderboardPageRead,
    PointMeRead,
    PointOutboxDrainRead,
    PointTransactionRead,
    PointTransactionsPageRead,
)
from app.domains.points.service.outbox_dispatcher import (
    OUTBOX_EVENT_POINTS_AWARDED,
    drain_points_outbox,
)
from app.infrastructure.cache.service import cache_service, keys

logger = logging.getLogger(__name__)

REASON_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


async def award_points(
    db: AsyncSession,
    *,
    payload: PointAwardCreate,
    actor: User,
    redis: Redis | None = None,
) -> tuple[PointLedger, int]:
    _validate_award_payload(payload)
    now = datetime.datetime.now(datetime.timezone.utc)

    participant = await crud.get_participant_for_update(db, participant_id=payload.participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    existing = await crud.get_entry_by_idempotency_key(db, idempotency_key=payload.idempotency_key)
    if existing:
        _ensure_same_idempotent_payload(existing=existing, payload=payload, actor_id=actor.id)
        return existing, existing.resulting_balance

    projection = await crud.get_projection_for_update(db, participant_id=payload.participant_id)
    if projection is None:
        try:
            projection = await crud.create_projection(
                db,
                participant_id=payload.participant_id,
                total_points=0,
                last_activity_at=now,
            )
        except IntegrityError:
            projection = await crud.get_projection_for_update(
                db, participant_id=payload.participant_id
            )
            if projection is None:
                raise

    current_balance = projection.total_points
    projected_balance = current_balance + payload.amount
    if projected_balance < 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient points balance")

    try:
        async with db.begin_nested():
            entry = await crud.create_ledger_entry(
                db,
                payload=payload,
                awarded_by_user_id=actor.id,
                resulting_balance=projected_balance,
            )
    except IntegrityError:
        existing = await crud.get_entry_by_idempotency_key(db, idempotency_key=payload.idempotency_key)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="idempotency conflict detected; retry with a new key",
            )
        _ensure_same_idempotent_payload(existing=existing, payload=payload, actor_id=actor.id)
        return existing, existing.resulting_balance

    await crud.update_projection(
        db,
        projection=projection,
        total_points=projected_balance,
        last_activity_at=entry.created_at,
    )
    await crud.enqueue_outbox_event(
        db,
        event_type=OUTBOX_EVENT_POINTS_AWARDED,
        participant_id=payload.participant_id,
        delta=payload.amount,
        resulting_balance=projected_balance,
        last_activity_at=entry.created_at,
        next_attempt_at=now,
    )

    if redis is not None:
        add_post_commit_hook(db, _drain_outbox_post_commit_hook(db, redis))

    return entry, projected_balance


async def get_my_points_summary(
    db: AsyncSession, *, user: User, recent_limit: int = 20
) -> PointMeRead:
    participant = await get_participant_by_user_id(db, user.id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant profile not found")

    balance = await crud.get_balance_for_participant(db, participant_id=participant.id)
    txs = await crud.list_participant_transactions(
        db, participant_id=participant.id, limit=recent_limit
    )
    return PointMeRead(
        participant_id=participant.id,
        balance=balance,
        recent_transactions=[serialize_transaction(tx) for tx in txs],
    )


async def get_leaderboard(
    db: AsyncSession,
    *,
    skip: int,
    limit: int,
    redis: Redis | None = None,
) -> PointLeaderboardPageRead:
    if redis is not None:
        cached = await _get_leaderboard_from_cache(db, redis=redis, skip=skip, limit=limit)
        if cached is not None:
            return cached

    total_ranked, rows = await crud.get_leaderboard_page(db, skip=skip, limit=limit)
    entries = [
        PointLeaderboardEntry(
            rank=skip + index + 1,
            participant_id=row[0],
            display_name=row[1],
            points=row[2],
        )
        for index, row in enumerate(rows)
    ]
    return PointLeaderboardPageRead(total_ranked=total_ranked, skip=skip, limit=limit, entries=entries)


async def get_my_rank(
    db: AsyncSession, *, user: User, redis: Redis | None = None
) -> PointLeaderboardMeRead:
    participant = await get_participant_by_user_id(db, user.id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant profile not found")

    if redis is not None:
        cached_rank = await _get_rank_from_cache(redis=redis, participant_id=participant.id)
        if cached_rank is not None:
            rank, total_ranked, points = cached_rank
            return PointLeaderboardMeRead(
                participant_id=participant.id,
                rank=rank,
                total_ranked=total_ranked,
                points=points,
            )

    rank, total_ranked, points = await crud.get_participant_rank_and_balance(
        db, participant_id=participant.id
    )
    return PointLeaderboardMeRead(
        participant_id=participant.id, rank=rank, total_ranked=total_ranked, points=points
    )


async def get_transactions_for_admin(
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
    start_at = _normalize_utc_datetime(start_at, field_name="start_at")
    end_at = _normalize_utc_datetime(end_at, field_name="end_at")

    if min_amount is not None and max_amount is not None and min_amount > max_amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="min_amount cannot exceed max_amount")
    if start_at is not None and end_at is not None and start_at > end_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_at cannot exceed end_at")

    total = await crud.count_transactions(
        db,
        participant_id=participant_id,
        reason=reason,
        min_amount=min_amount,
        max_amount=max_amount,
        start_at=start_at,
        end_at=end_at,
    )
    txs = await crud.list_transactions(
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
    return PointTransactionsPageRead(
        total=total,
        skip=skip,
        limit=limit,
        transactions=[serialize_transaction(tx) for tx in txs],
    )


async def rebuild_leaderboard_cache(
    db: AsyncSession,
    *,
    redis: Redis | None,
) -> int:
    if redis is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis unavailable for cache rebuild",
        )

    totals = await crud.list_projection_totals(db)
    leaderboard_key = keys.leaderboard()
    temp_key = keys.leaderboard_rebuild_tmp()

    await cache_service.delete(redis, temp_key)
    for participant_id, points, last_activity_at in totals:
        participant_key = str(participant_id)
        await cache_service.zadd(redis, temp_key, participant_key, float(points))
        await cache_service.set(redis, keys.participant_points(participant_key), points)
        await cache_service.set(
            redis,
            keys.participant_points_last_activity(participant_key),
            int(last_activity_at.timestamp()),
        )

    if totals:
        await cache_service.rename(redis, temp_key, leaderboard_key)
    else:
        await cache_service.delete(redis, leaderboard_key)
    await cache_service.publish(
        redis,
        keys.channel_leaderboard(),
        {"event": "leaderboard.rebuilt", "total_ranked": len(totals)},
    )
    return len(totals)


async def drain_outbox_now(
    db: AsyncSession,
    *,
    redis: Redis | None,
    limit: int = 200,
) -> PointOutboxDrainRead:
    if redis is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis unavailable for outbox drain",
        )
    result = await drain_points_outbox(db, redis=redis, limit=limit)
    return PointOutboxDrainRead(
        processed=result.processed,
        sent=result.sent,
        failed=result.failed,
        remaining_ready=result.remaining_ready,
    )


def serialize_transaction(tx: PointLedger) -> PointTransactionRead:
    return PointTransactionRead(
        id=tx.id,
        participant_id=tx.participant_id,
        amount=tx.amount,
        reason=tx.reason,
        reference_id=tx.reference_id,
        idempotency_key=tx.idempotency_key,
        note=tx.note,
        resulting_balance=tx.resulting_balance,
        awarded_by_user_id=tx.awarded_by_user_id,
        created_at=tx.created_at,
    )


def _validate_award_payload(payload: PointAwardCreate) -> None:
    if payload.amount == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="amount must be non-zero")
    if not REASON_CODE_PATTERN.fullmatch(payload.reason):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason must be a namespaced code like zone.lock_hunt.complete",
        )
    if not payload.idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must not be blank",
        )


def _ensure_same_idempotent_payload(
    *, existing: PointLedger, payload: PointAwardCreate, actor_id: uuid.UUID
) -> None:
    if (
        existing.participant_id != payload.participant_id
        or existing.amount != payload.amount
        or existing.reason != payload.reason
        or existing.reference_id != payload.reference_id
        or existing.note != payload.note
        or existing.awarded_by_user_id != actor_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="idempotency_key already exists for a different payload",
        )


async def _get_leaderboard_from_cache(
    db: AsyncSession,
    *,
    redis: Redis,
    skip: int,
    limit: int,
) -> PointLeaderboardPageRead | None:
    try:
        total_ranked = await cache_service.zcard(redis, keys.leaderboard())
        if total_ranked == 0:
            return None
        page = await cache_service.zrevrange_with_scores(
            redis, keys.leaderboard(), skip, skip + limit - 1
        )
    except Exception:
        logger.exception("Failed to load leaderboard page from cache")
        return None

    parsed_page: list[tuple[uuid.UUID, int]] = []
    for member, score in page:
        try:
            parsed_page.append((uuid.UUID(str(member)), int(score)))
        except Exception:
            logger.warning("Skipping invalid leaderboard cache member=%s", member)

    page_ids = [participant_id for participant_id, _ in parsed_page]
    name_map = await crud.get_participant_display_names(db, participant_ids=page_ids)

    entries = [
        PointLeaderboardEntry(
            rank=skip + idx + 1,
            participant_id=participant_id,
            display_name=name_map.get(participant_id, str(participant_id)),
            points=points,
        )
        for idx, (participant_id, points) in enumerate(parsed_page)
    ]
    return PointLeaderboardPageRead(total_ranked=total_ranked, skip=skip, limit=limit, entries=entries)


async def _get_rank_from_cache(
    *,
    redis: Redis,
    participant_id: uuid.UUID,
) -> tuple[int | None, int, int] | None:
    try:
        participant_key = str(participant_id)
        total_ranked = await cache_service.zcard(redis, keys.leaderboard())
        if total_ranked == 0:
            return None

        rank = await cache_service.zrevrank(redis, keys.leaderboard(), participant_key)
        if rank is None:
            return None, total_ranked, 0

        cached_points = await cache_service.get_int(
            redis, keys.participant_points(participant_key)
        )
        if cached_points is None:
            score = await cache_service.zscore(redis, keys.leaderboard(), participant_key)
            cached_points = int(score) if score is not None else 0
        return int(rank) + 1, total_ranked, int(cached_points)
    except Exception:
        logger.exception("Failed to load leaderboard rank from cache")
        return None


def _drain_outbox_post_commit_hook(db: AsyncSession, redis: Redis):
    async def _hook() -> None:
        try:
            # Keep request-path drain opportunistic; bulk recovery is handled by daemon/admin drain.
            await drain_points_outbox(db, redis=redis, limit=20)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Failed to drain points outbox in post-commit hook")

    return _hook


def _normalize_utc_datetime(
    value: datetime.datetime | None, *, field_name: str
) -> datetime.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be timezone-aware",
        )
    return value.astimezone(datetime.timezone.utc)

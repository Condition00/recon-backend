import datetime
import asyncio
import logging
from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.points import crud
from app.infrastructure.cache.service import cache_service, keys

logger = logging.getLogger(__name__)

OUTBOX_EVENT_POINTS_AWARDED = "points.awarded"


@dataclass(slots=True)
class OutboxDrainResult:
    processed: int
    sent: int
    failed: int
    remaining_ready: int


async def drain_points_outbox(
    db: AsyncSession,
    *,
    redis: Redis,
    limit: int = 200,
) -> OutboxDrainResult:
    now = datetime.datetime.now(datetime.timezone.utc)
    events = await crud.claim_pending_outbox_events(db, now=now, limit=limit)
    sent = 0
    failed = 0

    for event in events:
        try:
            await _publish_points_awarded(
                redis=redis,
                participant_id=str(event.participant_id),
                delta=event.delta,
                balance=event.resulting_balance,
                last_activity_at=event.last_activity_at,
            )
            await crud.mark_outbox_sent(db, event=event, sent_at=now)
            sent += 1
        except Exception as exc:
            logger.exception("Failed to dispatch points outbox event", exc_info=exc)
            await crud.mark_outbox_failed(db, event=event, now=now, error=str(exc))
            failed += 1

    remaining_ready = await crud.count_pending_outbox_events(db, now=now)
    return OutboxDrainResult(
        processed=len(events),
        sent=sent,
        failed=failed,
        remaining_ready=remaining_ready,
    )


async def run_points_outbox_daemon(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    redis: Redis,
    stop_event: asyncio.Event,
    batch_limit: int = 200,
    poll_interval_seconds: float = 2.0,
) -> None:
    while not stop_event.is_set():
        processed = 0
        try:
            async with session_factory() as session:
                result = await drain_points_outbox(session, redis=redis, limit=batch_limit)
                processed = result.processed
                await session.commit()
        except Exception:
            logger.exception("Points outbox daemon iteration failed")

        wait_seconds = 0.05 if processed > 0 else poll_interval_seconds
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=wait_seconds)
        except TimeoutError:
            continue


async def _publish_points_awarded(
    *,
    redis: Redis,
    participant_id: str,
    delta: int,
    balance: int,
    last_activity_at: datetime.datetime,
) -> None:
    last_activity_epoch = int(last_activity_at.timestamp())
    await cache_service.zadd(
        redis,
        keys.leaderboard(),
        participant_id,
        float(balance),
    )
    await cache_service.set(redis, keys.participant_points(participant_id), balance)
    await cache_service.set(
        redis,
        keys.participant_points_last_activity(participant_id),
        last_activity_epoch,
    )
    await cache_service.publish(
        redis,
        keys.channel_leaderboard(),
        {
            "event": OUTBOX_EVENT_POINTS_AWARDED,
            "participant_id": participant_id,
            "delta": delta,
            "balance": balance,
            "last_activity_epoch": last_activity_epoch,
        },
    )

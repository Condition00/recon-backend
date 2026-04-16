import datetime
import uuid

from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.participants.models import Participant
from app.domains.points.models import ParticipantPoints, PointLedger, PointsOutbox
from app.domains.points.schemas import PointAwardCreate


async def get_participant_for_update(
    db: AsyncSession, *, participant_id: uuid.UUID
) -> Participant | None:
    stmt = select(Participant).where(Participant.id == participant_id).with_for_update()
    result = await db.exec(stmt)
    return result.one_or_none()


async def get_projection_for_update(
    db: AsyncSession, *, participant_id: uuid.UUID
) -> ParticipantPoints | None:
    stmt = (
        select(ParticipantPoints)
        .where(ParticipantPoints.participant_id == participant_id)
        .with_for_update()
    )
    result = await db.exec(stmt)
    return result.one_or_none()


async def create_projection(
    db: AsyncSession,
    *,
    participant_id: uuid.UUID,
    total_points: int = 0,
    last_activity_at: datetime.datetime,
) -> ParticipantPoints:
    projection = ParticipantPoints(
        participant_id=participant_id,
        total_points=total_points,
        last_activity_at=last_activity_at,
    )
    db.add(projection)
    await db.flush()
    return projection


async def get_entry_by_idempotency_key(
    db: AsyncSession, *, idempotency_key: str
) -> PointLedger | None:
    stmt = select(PointLedger).where(PointLedger.idempotency_key == idempotency_key)
    result = await db.exec(stmt)
    return result.one_or_none()


async def create_ledger_entry(
    db: AsyncSession,
    *,
    payload: PointAwardCreate,
    awarded_by_user_id: uuid.UUID | None,
    resulting_balance: int,
) -> PointLedger:
    entry = PointLedger(
        participant_id=payload.participant_id,
        amount=payload.amount,
        reason=payload.reason,
        reference_id=payload.reference_id,
        idempotency_key=payload.idempotency_key,
        note=payload.note,
        resulting_balance=resulting_balance,
        awarded_by_user_id=awarded_by_user_id,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


async def update_projection(
    db: AsyncSession,
    *,
    projection: ParticipantPoints,
    total_points: int,
    last_activity_at: datetime.datetime,
) -> ParticipantPoints:
    projection.total_points = total_points
    projection.last_activity_at = last_activity_at
    db.add(projection)
    await db.flush()
    return projection


async def enqueue_outbox_event(
    db: AsyncSession,
    *,
    event_type: str,
    participant_id: uuid.UUID,
    delta: int,
    resulting_balance: int,
    last_activity_at: datetime.datetime,
    next_attempt_at: datetime.datetime,
) -> PointsOutbox:
    event = PointsOutbox(
        event_type=event_type,
        participant_id=participant_id,
        delta=delta,
        resulting_balance=resulting_balance,
        last_activity_at=last_activity_at,
        next_attempt_at=next_attempt_at,
    )
    db.add(event)
    await db.flush()
    return event


async def claim_pending_outbox_events(
    db: AsyncSession, *, now: datetime.datetime, limit: int
) -> list[PointsOutbox]:
    stmt = (
        select(PointsOutbox)
        .where(PointsOutbox.sent_at.is_(None))
        .where(PointsOutbox.next_attempt_at <= now)
        .order_by(PointsOutbox.next_attempt_at.asc(), PointsOutbox.created_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    result = await db.exec(stmt)
    return list(result.all())


async def mark_outbox_sent(
    db: AsyncSession, *, event: PointsOutbox, sent_at: datetime.datetime
) -> None:
    event.sent_at = sent_at
    event.last_error = None
    db.add(event)
    await db.flush()


async def mark_outbox_failed(
    db: AsyncSession,
    *,
    event: PointsOutbox,
    now: datetime.datetime,
    error: str,
) -> None:
    event.attempts += 1
    # Exponential backoff by attempt count, capped at 300 seconds.
    delay_seconds = min(2**event.attempts, 300)
    event.last_error = error[:1000]
    event.next_attempt_at = now + datetime.timedelta(seconds=delay_seconds)
    db.add(event)
    await db.flush()


async def count_pending_outbox_events(db: AsyncSession, *, now: datetime.datetime) -> int:
    stmt = (
        select(func.count(col(PointsOutbox.id)))
        .where(PointsOutbox.sent_at.is_(None))
        .where(PointsOutbox.next_attempt_at <= now)
    )
    result = await db.exec(stmt)
    return int(result.one())


async def get_balance_for_participant(
    db: AsyncSession, *, participant_id: uuid.UUID
) -> int:
    stmt = select(ParticipantPoints.total_points).where(
        ParticipantPoints.participant_id == participant_id
    )
    result = await db.exec(stmt)
    balance = result.one_or_none()
    return int(balance) if balance is not None else 0


async def list_participant_transactions(
    db: AsyncSession,
    *,
    participant_id: uuid.UUID,
    limit: int,
) -> list[PointLedger]:
    stmt = (
        select(PointLedger)
        .where(PointLedger.participant_id == participant_id)
        .order_by(PointLedger.created_at.desc(), PointLedger.id.desc())
        .limit(limit)
    )
    result = await db.exec(stmt)
    return list(result.all())


async def list_transactions(
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
) -> list[PointLedger]:
    stmt = select(PointLedger)
    if participant_id:
        stmt = stmt.where(PointLedger.participant_id == participant_id)
    if reason:
        stmt = stmt.where(PointLedger.reason == reason)
    if min_amount is not None:
        stmt = stmt.where(PointLedger.amount >= min_amount)
    if max_amount is not None:
        stmt = stmt.where(PointLedger.amount <= max_amount)
    if start_at is not None:
        stmt = stmt.where(PointLedger.created_at >= start_at)
    if end_at is not None:
        stmt = stmt.where(PointLedger.created_at <= end_at)

    stmt = stmt.order_by(PointLedger.created_at.desc(), PointLedger.id.desc()).offset(skip).limit(limit)
    result = await db.exec(stmt)
    return list(result.all())


async def count_transactions(
    db: AsyncSession,
    *,
    participant_id: uuid.UUID | None,
    reason: str | None,
    min_amount: int | None,
    max_amount: int | None,
    start_at: datetime.datetime | None,
    end_at: datetime.datetime | None,
) -> int:
    stmt = select(func.count(col(PointLedger.id)))
    if participant_id:
        stmt = stmt.where(PointLedger.participant_id == participant_id)
    if reason:
        stmt = stmt.where(PointLedger.reason == reason)
    if min_amount is not None:
        stmt = stmt.where(PointLedger.amount >= min_amount)
    if max_amount is not None:
        stmt = stmt.where(PointLedger.amount <= max_amount)
    if start_at is not None:
        stmt = stmt.where(PointLedger.created_at >= start_at)
    if end_at is not None:
        stmt = stmt.where(PointLedger.created_at <= end_at)
    result = await db.exec(stmt)
    return int(result.one())


async def get_leaderboard_page(
    db: AsyncSession, *, skip: int, limit: int
) -> tuple[int, list[tuple[uuid.UUID, str, int, datetime.datetime]]]:
    total_stmt = select(func.count()).select_from(ParticipantPoints)
    total_result = await db.exec(total_stmt)
    total_ranked = int(total_result.one())

    stmt = (
        select(
            Participant.id,
            Participant.display_name,
            ParticipantPoints.total_points,
            ParticipantPoints.last_activity_at,
        )
        .join(ParticipantPoints, ParticipantPoints.participant_id == Participant.id)
        .order_by(
            ParticipantPoints.total_points.desc(),
            ParticipantPoints.last_activity_at.desc(),
            Participant.id.asc(),
        )
        .offset(skip)
        .limit(limit)
    )
    result = await db.exec(stmt)
    rows = [(row[0], row[1], int(row[2]), row[3]) for row in result.all()]
    return total_ranked, rows


async def list_projection_totals(
    db: AsyncSession,
) -> list[tuple[uuid.UUID, int, datetime.datetime]]:
    stmt = select(
        ParticipantPoints.participant_id,
        ParticipantPoints.total_points,
        ParticipantPoints.last_activity_at,
    )
    result = await db.exec(stmt)
    return [(row[0], int(row[1]), row[2]) for row in result.all()]


async def get_participant_rank_and_balance(
    db: AsyncSession, *, participant_id: uuid.UUID
) -> tuple[int | None, int, int]:
    total_stmt = select(func.count()).select_from(ParticipantPoints)
    total_ranked_result = await db.exec(total_stmt)
    total_ranked = int(total_ranked_result.one())

    participant_stmt = select(
        ParticipantPoints.total_points,
        ParticipantPoints.last_activity_at,
    ).where(ParticipantPoints.participant_id == participant_id)
    participant_result = await db.exec(participant_stmt)
    participant_row = participant_result.one_or_none()
    if participant_row is None:
        return None, total_ranked, 0

    points = int(participant_row[0])
    last_activity_at = participant_row[1]
    rank_stmt = (
        select(func.count())
        .select_from(ParticipantPoints)
        .where(
            (ParticipantPoints.total_points > points)
            | (
                (ParticipantPoints.total_points == points)
                & (ParticipantPoints.last_activity_at > last_activity_at)
            )
            | (
                (ParticipantPoints.total_points == points)
                & (ParticipantPoints.last_activity_at == last_activity_at)
                & (ParticipantPoints.participant_id < participant_id)
            )
        )
    )
    rank_result = await db.exec(rank_stmt)
    rank = int(rank_result.one()) + 1
    return rank, total_ranked, points


async def get_participant_display_names(
    db: AsyncSession, *, participant_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    if not participant_ids:
        return {}
    stmt = select(Participant.id, Participant.display_name).where(
        Participant.id.in_(participant_ids)
    )
    result = await db.exec(stmt)
    return {row[0]: row[1] for row in result.all()}

import datetime
import logging
import re
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

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
    PointTransactionRead,
    PointTransactionsPageRead,
)

logger = logging.getLogger(__name__)

REASON_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


async def award_points(
    db: AsyncSession,
    *,
    payload: PointAwardCreate,
    actor: User,
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
) -> PointLeaderboardPageRead:
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
    db: AsyncSession, *, user: User
) -> PointLeaderboardMeRead:
    participant = await get_participant_by_user_id(db, user.id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant profile not found")

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

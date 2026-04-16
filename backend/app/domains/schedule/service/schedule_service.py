import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.schedule import crud
from app.domains.schedule.models import SessionType
from app.domains.schedule.schemas import (
    SessionCreate, SessionUpdate, SessionDetailRead, SessionRead,
    SpeakerCreate, SpeakerUpdate, SpeakerRead,
)


# --- Session Services ---

async def get_schedule(
    db: AsyncSession,
    *,
    day: Optional[datetime] = None,
    zone_id: Optional[uuid.UUID] = None,
    session_type: Optional[SessionType] = None,
    is_admin: bool = False,
) -> list[SessionRead]:
    sessions = await crud.list_sessions(
        db,
        day=day,
        zone_id=zone_id,
        session_type=session_type,
        published_only=not is_admin,
    )
    return [SessionRead.model_validate(s) for s in sessions]


async def get_session_detail(db: AsyncSession, session_id: uuid.UUID) -> SessionDetailRead:
    session = await crud.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    speakers = await crud.get_speakers_for_session(db, session_id)
    result = SessionDetailRead.model_validate(session)
    result.speakers = [SpeakerRead.model_validate(sp) for sp in speakers]
    return result


async def create_session(db: AsyncSession, *, payload: SessionCreate) -> SessionRead:
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ends_at must be after starts_at",
        )
    session = await crud.create_session(db, payload=payload)
    return SessionRead.model_validate(session)


async def update_session(db: AsyncSession, session_id: uuid.UUID, payload: SessionUpdate) -> SessionRead:
    session = await crud.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    updated = await crud.update_session(db, session, payload)
    return SessionRead.model_validate(updated)


async def delete_session(db: AsyncSession, session_id: uuid.UUID) -> None:
    session = await crud.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    await crud.delete_session(db, session)


# --- Speaker Services ---

async def get_all_speakers(db: AsyncSession) -> list[SpeakerRead]:
    speakers = await crud.list_speakers(db)
    return [SpeakerRead.model_validate(sp) for sp in speakers]


async def create_speaker(db: AsyncSession, *, payload: SpeakerCreate) -> SpeakerRead:
    speaker = await crud.create_speaker(db, payload=payload)
    return SpeakerRead.model_validate(speaker)


async def update_speaker(db: AsyncSession, speaker_id: uuid.UUID, payload: SpeakerUpdate) -> SpeakerRead:
    speaker = await crud.get_speaker_by_id(db, speaker_id)
    if not speaker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Speaker not found")
    updated = await crud.update_speaker(db, speaker, payload)
    return SpeakerRead.model_validate(updated)


async def delete_speaker(db: AsyncSession, speaker_id: uuid.UUID) -> None:
    speaker = await crud.get_speaker_by_id(db, speaker_id)
    if not speaker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Speaker not found")
    await crud.delete_speaker(db, speaker)


# --- Session-Speaker Link Services ---

async def attach_speaker_to_session(
    db: AsyncSession, *, session_id: uuid.UUID, speaker_id: uuid.UUID, display_order: int = 0
) -> None:
    session = await crud.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    speaker = await crud.get_speaker_by_id(db, speaker_id)
    if not speaker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Speaker not found")
    await crud.attach_speaker(db, session_id=session_id, speaker_id=speaker_id, display_order=display_order)


async def detach_speaker_from_session(
    db: AsyncSession, *, session_id: uuid.UUID, speaker_id: uuid.UUID
) -> None:
    await crud.detach_speaker(db, session_id=session_id, speaker_id=speaker_id)
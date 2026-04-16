import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.schedule.models import Session, Speaker, SessionSpeaker, SessionType
from app.domains.schedule.schemas import SessionCreate, SessionUpdate, SpeakerCreate, SpeakerUpdate


# --- Session CRUD ---

async def list_sessions(
    db: AsyncSession,
    *,
    day: Optional[datetime] = None,
    zone_id: Optional[uuid.UUID] = None,
    session_type: Optional[SessionType] = None,
    published_only: bool = True,
) -> list[Session]:
    query = select(Session)
    if published_only:
        query = query.where(Session.is_published == True)
    if day:
        query = query.where(Session.starts_at >= day.replace(hour=0, minute=0, second=0))
        query = query.where(Session.starts_at < day.replace(hour=23, minute=59, second=59))
    if zone_id:
        query = query.where(Session.zone_id == zone_id)
    if session_type:
        query = query.where(Session.session_type == session_type)
    query = query.order_by(Session.starts_at.asc())
    result = await db.exec(query)
    return list(result.all())


async def get_session_by_id(db: AsyncSession, session_id: uuid.UUID) -> Session | None:
    return await db.get(Session, session_id)


async def create_session(db: AsyncSession, *, payload: SessionCreate) -> Session:
    session = Session(**payload.model_dump())
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def update_session(db: AsyncSession, session: Session, payload: SessionUpdate) -> Session:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(session, key, value)
    await db.flush()
    await db.refresh(session)
    return session


async def delete_session(db: AsyncSession, session: Session) -> None:
    await db.delete(session)
    await db.flush()


# --- Speaker CRUD ---

async def list_speakers(db: AsyncSession) -> list[Speaker]:
    result = await db.exec(select(Speaker))
    return list(result.all())


async def get_speaker_by_id(db: AsyncSession, speaker_id: uuid.UUID) -> Speaker | None:
    return await db.get(Speaker, speaker_id)


async def create_speaker(db: AsyncSession, *, payload: SpeakerCreate) -> Speaker:
    speaker = Speaker(**payload.model_dump())
    db.add(speaker)
    await db.flush()
    await db.refresh(speaker)
    return speaker


async def update_speaker(db: AsyncSession, speaker: Speaker, payload: SpeakerUpdate) -> Speaker:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(speaker, key, value)
    await db.flush()
    await db.refresh(speaker)
    return speaker


async def delete_speaker(db: AsyncSession, speaker: Speaker) -> None:
    await db.delete(speaker)
    await db.flush()


# --- SessionSpeaker CRUD ---

async def get_speakers_for_session(db: AsyncSession, session_id: uuid.UUID) -> list[Speaker]:
    query = (
        select(Speaker)
        .join(SessionSpeaker, SessionSpeaker.speaker_id == Speaker.id)
        .where(SessionSpeaker.session_id == session_id)
        .order_by(SessionSpeaker.display_order.asc())
    )
    result = await db.exec(query)
    return list(result.all())


async def attach_speaker(
    db: AsyncSession, *, session_id: uuid.UUID, speaker_id: uuid.UUID, display_order: int = 0
) -> SessionSpeaker:
    link = SessionSpeaker(session_id=session_id, speaker_id=speaker_id, display_order=display_order)
    db.add(link)
    await db.flush()
    return link


async def detach_speaker(db: AsyncSession, *, session_id: uuid.UUID, speaker_id: uuid.UUID) -> None:
    query = select(SessionSpeaker).where(
        SessionSpeaker.session_id == session_id,
        SessionSpeaker.speaker_id == speaker_id,
    )
    result = await db.exec(query)
    link = result.first()
    if link:
        await db.delete(link)
        await db.flush()
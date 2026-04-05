import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.participants.models import Participant
from app.domains.participants.schemas import ParticipantCreate


async def get_participant_by_id(db: AsyncSession, participant_id: uuid.UUID) -> Participant | None:
    return await db.get(Participant, participant_id)


async def get_participant_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> Participant | None:
    result = await db.exec(select(Participant).where(Participant.user_id == user_id))
    return result.one_or_none()


async def get_participant_by_display_name(db: AsyncSession, display_name: str) -> Participant | None:
    result = await db.exec(select(Participant).where(Participant.display_name == display_name))
    return result.one_or_none()


async def list_participants(
    db: AsyncSession, *, checked_in: bool | None = None, skip: int = 0, limit: int = 50
) -> list[Participant]:
    query = select(Participant)
    if checked_in is True:
        query = query.where(Participant.checked_in_at.is_not(None))
    elif checked_in is False:
        query = query.where(Participant.checked_in_at.is_(None))
    query = query.offset(skip).limit(limit).order_by(Participant.created_at.desc())
    result = await db.exec(query)
    return list(result.all())


async def create_participant(
    db: AsyncSession, *, user_id: uuid.UUID, payload: ParticipantCreate
) -> Participant:
    participant = Participant(
        user_id=user_id,
        display_name=payload.display_name,
        institution=payload.institution,
        year=payload.year,
        linkedin_acc=payload.linkedin_acc,
        github_acc=payload.github_acc,
        x_acc=payload.x_acc,
        phone=payload.phone,
        profile_photo_file_key=payload.profile_photo_file_key,
        talent_visible=payload.talent_visible,
        talent_contact_shareable=payload.talent_contact_shareable,
    )
    db.add(participant)
    await db.flush()
    await db.refresh(participant)
    return participant

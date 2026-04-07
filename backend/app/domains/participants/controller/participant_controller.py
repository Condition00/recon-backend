import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import User
from app.domains.participants.models import Participant
from app.domains.participants.schemas import (
    ParticipantCreate,
    ParticipantRead,
    ParticipantTalentVisibilityUpdate,
    ParticipantUpdate,
)
from app.domains.participants.service import (
    check_in_participant,
    create_my_participant_profile,
    get_my_participant_profile,
    get_participant_for_view,
    list_participants_for_admin,
    serialize_participant_for_user,
    serialize_participant_list_item,
    update_my_participant_profile,
    update_my_talent_visibility,
)


async def create_me(db: AsyncSession, user: User, payload: ParticipantCreate) -> ParticipantRead:
    participant = await create_my_participant_profile(db, user=user, payload=payload)
    return serialize_participant_for_user(participant, user)


async def get_me(db: AsyncSession, user: User) -> ParticipantRead:
    participant = await get_my_participant_profile(db, user=user)
    return serialize_participant_for_user(participant, user)


async def update_me(db: AsyncSession, user: User, payload: ParticipantUpdate) -> ParticipantRead:
    participant = await update_my_participant_profile(db, user=user, payload=payload)
    return serialize_participant_for_user(participant, user)


async def update_visibility(
    db: AsyncSession, user: User, payload: ParticipantTalentVisibilityUpdate
) -> ParticipantRead:
    participant = await update_my_talent_visibility(db, user=user, payload=payload)
    return serialize_participant_for_user(participant, user)


async def get_one(db: AsyncSession, participant_id: uuid.UUID, user: User) -> ParticipantRead:
    return await get_participant_for_view(db, participant_id=participant_id, current_user=user)


async def list_all(
    db: AsyncSession, checked_in: bool | None = None, skip: int = 0, limit: int = 50
) -> list[ParticipantRead]:
    participants = await list_participants_for_admin(db, checked_in=checked_in, skip=skip, limit=limit)
    return [serialize_participant_list_item(participant) for participant in participants]


async def check_in(db: AsyncSession, participant_id: uuid.UUID, user: User) -> Participant:
    return await check_in_participant(db, participant_id=participant_id, checked_in_by=user)

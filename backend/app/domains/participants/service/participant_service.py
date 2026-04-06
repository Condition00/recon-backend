import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import ROLE_ADMIN, User
from app.domains.participants.crud import (
    create_participant,
    get_participant_by_display_name,
    get_participant_by_id,
    get_participant_by_user_id,
    list_participants,
)
from app.domains.participants.models import Participant
from app.domains.participants.schemas import (
    ParticipantCreate,
    ParticipantRead,
    ParticipantTalentVisibilityUpdate,
    ParticipantUpdate,
)


async def create_my_participant_profile(
    db: AsyncSession, *, user: User, payload: ParticipantCreate
) -> Participant:
    existing = await get_participant_by_user_id(db, user.id)
    if existing:
        raise HTTPException(status_code=409, detail="Participant profile already exists for this account")

    duplicate_name = await get_participant_by_display_name(db, payload.display_name)
    if duplicate_name:
        raise HTTPException(status_code=409, detail="Display name is already in use")

    return await create_participant(db, user_id=user.id, payload=payload)


async def get_my_participant_profile(db: AsyncSession, *, user: User) -> Participant:
    participant = await get_participant_by_user_id(db, user.id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant profile not found")
    return participant


async def update_my_participant_profile(
    db: AsyncSession, *, user: User, payload: ParticipantUpdate
) -> Participant:
    participant = await get_my_participant_profile(db, user=user)
    updates = payload.model_dump(exclude_unset=True)

    display_name = updates.get("display_name")
    if display_name and display_name != participant.display_name:
        duplicate_name = await get_participant_by_display_name(db, display_name)
        if duplicate_name:
            raise HTTPException(status_code=409, detail="Display name is already in use")

    for field, value in updates.items():
        setattr(participant, field, value)

    await db.flush()
    await db.refresh(participant)
    return participant


async def update_my_talent_visibility(
    db: AsyncSession, *, user: User, payload: ParticipantTalentVisibilityUpdate
) -> Participant:
    participant = await get_my_participant_profile(db, user=user)
    participant.talent_visible = payload.talent_visible
    participant.talent_contact_shareable = payload.talent_contact_shareable
    await db.flush()
    await db.refresh(participant)
    return participant


async def get_participant_for_view(
    db: AsyncSession, *, participant_id: uuid.UUID, current_user: User
) -> ParticipantRead:
    participant = await get_participant_by_id(db, participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    return _serialize_participant(participant, current_user=current_user)


async def list_participants_for_admin(
    db: AsyncSession, *, checked_in: bool | None = None, skip: int = 0, limit: int = 50
) -> list[Participant]:
    return await list_participants(db, checked_in=checked_in, skip=skip, limit=limit)


async def check_in_participant(
    db: AsyncSession, *, participant_id: uuid.UUID, checked_in_by: User
) -> Participant:
    participant = await get_participant_by_id(db, participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    participant.checked_in_at = datetime.now(timezone.utc)
    participant.checked_in_by = checked_in_by.id
    await db.flush()
    await db.refresh(participant)
    return participant


def serialize_participant_list_item(participant: Participant) -> ParticipantRead:
    return _serialize_participant(participant, current_user=None, force_admin_view=True)


def serialize_participant_for_user(participant: Participant, current_user: User) -> ParticipantRead:
    return _serialize_participant(participant, current_user=current_user)


def _serialize_participant(
    participant: Participant, *, current_user: User | None, force_admin_view: bool = False
) -> ParticipantRead:
    viewer_role = current_user.role.name if current_user and current_user.role else None
    is_owner = current_user is not None and participant.user_id == current_user.id
    is_admin = viewer_role == ROLE_ADMIN or force_admin_view

    can_view_contact = is_owner or is_admin or (
        participant.talent_visible and participant.talent_contact_shareable
    )
    can_view_social = is_owner or is_admin or participant.talent_visible

    return ParticipantRead(
        id=participant.id,
        user_id=participant.user_id,
        display_name=participant.display_name,
        institution=participant.institution,
        year=participant.year,
        linkedin_acc=participant.linkedin_acc if can_view_social else None,
        github_acc=participant.github_acc if can_view_social else None,
        x_acc=participant.x_acc if can_view_social else None,
        phone=participant.phone if can_view_contact else None,
        profile_photo_file_key=participant.profile_photo_file_key,
        talent_visible=participant.talent_visible,
        talent_contact_shareable=participant.talent_contact_shareable,
        checked_in_at=participant.checked_in_at if (is_owner or is_admin) else None,
        checked_in_by=participant.checked_in_by if is_admin else None,
        created_at=participant.created_at,
        can_edit=is_owner,
        is_self=is_owner,
    )

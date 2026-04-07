import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.domains.auth.models import ROLE_ADMIN, User
from app.domains.participants.controller import (
    check_in,
    create_me,
    get_me,
    get_one,
    list_all,
    update_me,
    update_visibility,
)
from app.domains.participants.schemas import (
    ParticipantCheckInRead,
    ParticipantCreate,
    ParticipantRead,
    ParticipantTalentVisibilityUpdate,
    ParticipantUpdate,
)
from app.utils.deps import get_current_user, require_roles

router = APIRouter(prefix="/participants", tags=["participants"])


@router.post("/me", response_model=ParticipantRead, status_code=status.HTTP_201_CREATED)
async def create_my_profile(
    payload: ParticipantCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await create_me(db, user, payload)


@router.get("/me", response_model=ParticipantRead)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await get_me(db, user)


@router.patch("/me", response_model=ParticipantRead)
async def update_my_profile(
    payload: ParticipantUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await update_me(db, user, payload)


@router.patch("/me/talent-visibility", response_model=ParticipantRead)
async def update_my_talent_preferences(
    payload: ParticipantTalentVisibilityUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await update_visibility(db, user, payload)


@router.get("/{participant_id}", response_model=ParticipantRead)
async def get_participant(
    participant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await get_one(db, participant_id, user)


@router.get("/", response_model=list[ParticipantRead])
async def list_participant_profiles(
    checked_in: bool | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(ROLE_ADMIN)),
):
    return await list_all(db, checked_in=checked_in, skip=skip, limit=limit)


@router.post("/{participant_id}/checkin", response_model=ParticipantCheckInRead)
async def check_in_profile(
    participant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(ROLE_ADMIN)),
):
    return await check_in(db, participant_id, user)

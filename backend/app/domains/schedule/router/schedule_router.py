import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import ROLE_ADMIN
from app.domains.schedule.controller.schedule_controller import schedule_controller
from app.domains.schedule.models import SessionType
from app.domains.schedule.schemas import (
    SessionCreate, SessionUpdate, SessionDetailRead, SessionRead,
    SpeakerCreate, SpeakerUpdate, SpeakerRead,
)
from app.utils.deps import get_db, require_roles

router = APIRouter(prefix="/schedule", tags=["schedule"])


# --- Participant routes ---

@router.get("", response_model=list[SessionRead])
async def list_sessions(
    day: Optional[datetime] = None,
    zone_id: Optional[uuid.UUID] = None,
    session_type: Optional[SessionType] = None,
    db: AsyncSession = Depends(get_db),
):
    return await schedule_controller.list_sessions(
        db, day=day, zone_id=zone_id, session_type=session_type, is_admin=False
    )


@router.get("/{session_id}", response_model=SessionDetailRead)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await schedule_controller.get_session(db, session_id)


# --- Admin routes ---

@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles(ROLE_ADMIN))])
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
):
    return await schedule_controller.create_session(db, payload)


@router.patch("/{session_id}", response_model=SessionRead,
              dependencies=[Depends(require_roles(ROLE_ADMIN))])
async def update_session(
    session_id: uuid.UUID,
    payload: SessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await schedule_controller.update_session(db, session_id, payload)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(ROLE_ADMIN))])
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await schedule_controller.delete_session(db, session_id)


@router.post("/{session_id}/speakers", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=[Depends(require_roles(ROLE_ADMIN))])
async def attach_speaker(
    session_id: uuid.UUID,
    speaker_id: uuid.UUID,
    display_order: int = 0,
    db: AsyncSession = Depends(get_db),
):
    await schedule_controller.attach_speaker(db, session_id, speaker_id, display_order)


@router.delete("/{session_id}/speakers/{speaker_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(ROLE_ADMIN))])
async def detach_speaker(
    session_id: uuid.UUID,
    speaker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await schedule_controller.detach_speaker(db, session_id, speaker_id)


# --- Speaker management ---

@router.get("/speakers/all", response_model=list[SpeakerRead])
async def list_speakers(db: AsyncSession = Depends(get_db)):
    return await schedule_controller.list_speakers(db)


@router.post("/speakers", response_model=SpeakerRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles(ROLE_ADMIN))])
async def create_speaker(
    payload: SpeakerCreate,
    db: AsyncSession = Depends(get_db),
):
    return await schedule_controller.create_speaker(db, payload)


@router.patch("/speakers/{speaker_id}", response_model=SpeakerRead,
              dependencies=[Depends(require_roles(ROLE_ADMIN))])
async def update_speaker(
    speaker_id: uuid.UUID,
    payload: SpeakerUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await schedule_controller.update_speaker(db, speaker_id, payload)


@router.delete("/speakers/{speaker_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(ROLE_ADMIN))])
async def delete_speaker(
    speaker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await schedule_controller.delete_speaker(db, speaker_id)
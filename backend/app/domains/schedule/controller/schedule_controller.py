import uuid
from datetime import datetime
from typing import Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.schedule.models import SessionType
from app.domains.schedule.schemas import (
    SessionCreate, SessionUpdate, SessionDetailRead, SessionRead,
    SpeakerCreate, SpeakerUpdate, SpeakerRead,
)
from app.domains.schedule.service import schedule_service


class ScheduleController:

    # --- Sessions ---

    async def list_sessions(
        self,
        db: AsyncSession,
        *,
        day: Optional[datetime] = None,
        zone_id: Optional[uuid.UUID] = None,
        session_type: Optional[SessionType] = None,
        is_admin: bool = False,
    ) -> list[SessionRead]:
        return await schedule_service.get_schedule(
            db, day=day, zone_id=zone_id, session_type=session_type, is_admin=is_admin
        )

    async def get_session(self, db: AsyncSession, session_id: uuid.UUID) -> SessionDetailRead:
        return await schedule_service.get_session_detail(db, session_id)

    async def create_session(self, db: AsyncSession, payload: SessionCreate) -> SessionRead:
        return await schedule_service.create_session(db, payload=payload)

    async def update_session(
        self, db: AsyncSession, session_id: uuid.UUID, payload: SessionUpdate
    ) -> SessionRead:
        return await schedule_service.update_session(db, session_id, payload)

    async def delete_session(self, db: AsyncSession, session_id: uuid.UUID) -> None:
        return await schedule_service.delete_session(db, session_id)

    # --- Speakers ---

    async def list_speakers(self, db: AsyncSession) -> list[SpeakerRead]:
        return await schedule_service.get_all_speakers(db)

    async def create_speaker(self, db: AsyncSession, payload: SpeakerCreate) -> SpeakerRead:
        return await schedule_service.create_speaker(db, payload=payload)

    async def update_speaker(
        self, db: AsyncSession, speaker_id: uuid.UUID, payload: SpeakerUpdate
    ) -> SpeakerRead:
        return await schedule_service.update_speaker(db, speaker_id, payload)

    async def delete_speaker(self, db: AsyncSession, speaker_id: uuid.UUID) -> None:
        return await schedule_service.delete_speaker(db, speaker_id)

    # --- Session-Speaker Links ---

    async def attach_speaker(
        self, db: AsyncSession, session_id: uuid.UUID, speaker_id: uuid.UUID, display_order: int = 0
    ) -> None:
        return await schedule_service.attach_speaker_to_session(
            db, session_id=session_id, speaker_id=speaker_id, display_order=display_order
        )

    async def detach_speaker(
        self, db: AsyncSession, session_id: uuid.UUID, speaker_id: uuid.UUID
    ) -> None:
        return await schedule_service.detach_speaker_from_session(
            db, session_id=session_id, speaker_id=speaker_id
        )


schedule_controller = ScheduleController()
import uuid
from typing import Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.incidents import service
from app.domains.incidents.models import Incident, IncidentSeverity, IncidentStatus
from app.domains.incidents.schemas import IncidentCreate, IncidentUpdate


async def create(db: AsyncSession, *, obj_in: IncidentCreate, reported_by: uuid.UUID) -> Incident:
    return await service.create_incident(db, obj_in=obj_in, reported_by=reported_by)


async def get(db: AsyncSession, *, incident_id: uuid.UUID) -> Incident:
    return await service.get_incident(db, incident_id=incident_id)


async def list_all(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    status: Optional[IncidentStatus] = None,
    severity: Optional[IncidentSeverity] = None,
) -> list[Incident]:
    return await service.list_incidents(
        db, skip=skip, limit=limit, status_filter=status, severity_filter=severity
    )


async def update(db: AsyncSession, *, incident_id: uuid.UUID, obj_in: IncidentUpdate) -> Incident:
    return await service.update_incident(db, incident_id=incident_id, obj_in=obj_in)

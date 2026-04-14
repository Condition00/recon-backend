import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.incidents import crud
from app.domains.incidents.models import Incident, IncidentSeverity, IncidentStatus
from app.domains.incidents.schemas import IncidentCreate, IncidentUpdate


async def create_incident(
    db: AsyncSession, *, obj_in: IncidentCreate, reported_by: Optional[uuid.UUID] = None
) -> Incident:
    """Create a new incident."""
    return await crud.create(db=db, obj_in=obj_in, reported_by=reported_by)


async def get_incident(db: AsyncSession, *, incident_id: uuid.UUID) -> Incident:
    """Get an incident by ID. Raises 404 if not found."""
    incident = await crud.get(db=db, id=incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


async def list_incidents(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[IncidentStatus] = None,
    severity_filter: Optional[IncidentSeverity] = None,
) -> list[Incident]:
    """List incidents with optional filters."""
    return await crud.get_multi(
        db=db, skip=skip, limit=limit, status=status_filter, severity=severity_filter
    )


async def update_incident(
    db: AsyncSession, *, incident_id: uuid.UUID, obj_in: IncidentUpdate
) -> Incident:
    """Update an incident. Handles status transitions (e.g. setting resolved_at)."""
    incident = await get_incident(db, incident_id=incident_id)

    update_data = obj_in.model_dump(exclude_unset=True)

    # If transitioning to resolved, stamp resolved_at
    if "status" in update_data and update_data["status"] == IncidentStatus.resolved:
        if incident.status != IncidentStatus.resolved:
            update_data["resolved_at"] = datetime.now(timezone.utc)
    # If transitioning away from resolved, clear resolved_at
    elif "status" in update_data and update_data["status"] != IncidentStatus.resolved:
        if incident.status == IncidentStatus.resolved:
            update_data["resolved_at"] = None

    return await crud.update(db=db, db_obj=incident, obj_in=update_data)

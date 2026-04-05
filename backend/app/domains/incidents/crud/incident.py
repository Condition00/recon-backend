import uuid
from typing import Any, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.incidents.models import Incident, IncidentSeverity, IncidentStatus
from app.domains.incidents.schemas import IncidentCreate, IncidentUpdate


async def create(db: AsyncSession, *, obj_in: IncidentCreate, reported_by: Optional[uuid.UUID] = None) -> Incident:
    db_obj = Incident.model_validate(obj_in)
    if reported_by:
        db_obj.reported_by = reported_by
    
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj


async def get(db: AsyncSession, id: uuid.UUID) -> Optional[Incident]:
    return await db.get(Incident, id)


async def get_multi(
    db: AsyncSession, *, skip: int = 0, limit: int = 100,
    status: Optional[IncidentStatus] = None,
    severity: Optional[IncidentSeverity] = None
) -> list[Incident]:
    stmt = select(Incident)
    
    if status is not None:
        stmt = stmt.where(Incident.status == status)
    if severity is not None:
        stmt = stmt.where(Incident.severity == severity)
        
    stmt = stmt.order_by(Incident.created_at.desc()).offset(skip).limit(limit)
    result = await db.exec(stmt)
    return list(result.all())


async def update(db: AsyncSession, *, db_obj: Incident, obj_in: IncidentUpdate | dict[str, Any]) -> Incident:
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        update_data = obj_in.model_dump(exclude_unset=True)
        
    for field, value in update_data.items():
        setattr(db_obj, field, value)
        
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj

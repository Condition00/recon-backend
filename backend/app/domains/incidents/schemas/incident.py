import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel

from app.domains.incidents.models.incident import IncidentBase, IncidentSeverity, IncidentStatus


class IncidentCreate(SQLModel):
    title: str
    description: str
    severity: IncidentSeverity = IncidentSeverity.low
    zone_id: Optional[uuid.UUID] = None


class IncidentUpdate(SQLModel):
    status: Optional[IncidentStatus] = None
    severity: Optional[IncidentSeverity] = None
    assigned_to: Optional[uuid.UUID] = None
    resolution_notes: Optional[str] = None


class IncidentRead(IncidentBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    reported_by: Optional[uuid.UUID] = None
    assigned_to: Optional[uuid.UUID] = None

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.utils.models.base import Base


class IncidentSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(str, enum.Enum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"


class IncidentBase(SQLModel):
    title: str = Field(max_length=255)
    description: str
    severity: IncidentSeverity = Field(default=IncidentSeverity.low)
    status: IncidentStatus = Field(default=IncidentStatus.open)
    zone_id: Optional[uuid.UUID] = Field(default=None)
    resolved_at: Optional[datetime] = Field(default=None)
    resolution_notes: Optional[str] = Field(default=None)


class Incident(Base, IncidentBase, table=True):
    __tablename__ = "incidents"

    reported_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)
    assigned_to: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)

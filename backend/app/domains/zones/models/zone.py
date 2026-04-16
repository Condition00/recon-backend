from enum import Enum

from sqlalchemy import JSON, Column, String
from sqlmodel import Field, SQLModel

from app.utils.models.base import Base


class ZoneStatus(str, Enum):
    green = "green"
    amber = "amber"
    red = "red"
    closed = "closed"


class ZoneBase(SQLModel):
    name: str = Field(max_length=120, index=True)
    short_name: str = Field(max_length=40, index=True, unique=True)
    category: str = Field(max_length=60, index=True)
    zone_type: str = Field(max_length=60, index=True)
    status: ZoneStatus = Field(
        default=ZoneStatus.green,
        sa_column=Column(String(length=20), nullable=False, server_default="green"),
    )
    location: str = Field(max_length=200)
    points: int = Field(default=0, ge=0)
    color: str = Field(max_length=40, default="#0EA5E9")
    tags: list[str] | None = Field(default=None, sa_column=Column(JSON))
    is_active: bool = Field(default=True, index=True)


class Zone(Base, ZoneBase, table=True):
    __tablename__ = "zones"

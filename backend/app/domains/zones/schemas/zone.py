import datetime
import uuid

from sqlmodel import SQLModel


class ZoneCatalogItemRead(SQLModel):
    id: uuid.UUID
    name: str
    shortName: str
    category: str
    type: str
    tags: list[str]
    status: str
    location: str
    points: int
    registeredCount: int
    color: str


class ZoneRead(ZoneCatalogItemRead):
    createdAt: datetime.datetime
    updatedAt: datetime.datetime


class ZoneRegistrationRead(SQLModel):
    zoneId: uuid.UUID
    isActive: bool
    code: str
    checkedInAt: datetime.datetime | None = None


class ZonePassRead(SQLModel):
    zoneId: uuid.UUID
    code: str
    isActive: bool
    checkedInAt: datetime.datetime | None = None


class MyRegistrationsRead(SQLModel):
    zoneIds: list[uuid.UUID]


class MyPassesRead(SQLModel):
    passes: list[ZonePassRead]

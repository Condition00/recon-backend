import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import User
from app.domains.zones.schemas import (
    MyPassesRead,
    MyRegistrationsRead,
    ZoneCatalogItemRead,
    ZoneRead,
    ZoneRegistrationRead,
)
from app.domains.zones.service import (
    get_zone_details,
    list_my_passes,
    list_my_registrations,
    list_zones,
    register_for_zone,
    unregister_from_zone,
)


async def get_catalog(db: AsyncSession) -> list[ZoneCatalogItemRead]:
    return await list_zones(db)


async def get_one(db: AsyncSession, *, zone_id: uuid.UUID) -> ZoneRead:
    return await get_zone_details(db, zone_id=zone_id)


async def register(
    db: AsyncSession, *, zone_id: uuid.UUID, user: User
) -> tuple[ZoneRegistrationRead, bool]:
    return await register_for_zone(db, zone_id=zone_id, user=user)


async def unregister(
    db: AsyncSession, *, zone_id: uuid.UUID, user: User
) -> ZoneRegistrationRead:
    return await unregister_from_zone(db, zone_id=zone_id, user=user)


async def my_registrations(
    db: AsyncSession, *, user: User
) -> MyRegistrationsRead:
    return await list_my_registrations(db, user=user)


async def my_passes(
    db: AsyncSession, *, user: User
) -> MyPassesRead:
    return await list_my_passes(db, user=user)

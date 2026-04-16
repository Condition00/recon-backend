import uuid

from sqlalchemy import case, func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.zones.models import Zone, ZoneRegistration


async def list_active_zones_with_registration_counts(
    db: AsyncSession,
) -> list[tuple[Zone, int]]:
    active_count = func.coalesce(
        func.sum(case((ZoneRegistration.is_active.is_(True), 1), else_=0)),
        0,
    )
    stmt = (
        select(Zone, active_count)
        .select_from(Zone)
        .join(ZoneRegistration, ZoneRegistration.zone_id == Zone.id, isouter=True)
        .where(Zone.is_active.is_(True))
        .group_by(Zone.id)
        .order_by(Zone.name.asc(), Zone.id.asc())
    )
    result = await db.exec(stmt)
    return [(row[0], int(row[1])) for row in result.all()]


async def get_zone_with_registration_count(
    db: AsyncSession, *, zone_id: uuid.UUID
) -> tuple[Zone, int] | None:
    active_count = func.coalesce(
        func.sum(case((ZoneRegistration.is_active.is_(True), 1), else_=0)),
        0,
    )
    stmt = (
        select(Zone, active_count)
        .select_from(Zone)
        .join(ZoneRegistration, ZoneRegistration.zone_id == Zone.id, isouter=True)
        .where(Zone.id == zone_id)
        .where(Zone.is_active.is_(True))
        .group_by(Zone.id)
    )
    result = await db.exec(stmt)
    row = result.one_or_none()
    if row is None:
        return None
    return row[0], int(row[1])


async def get_zone_by_id(
    db: AsyncSession, *, zone_id: uuid.UUID
) -> Zone | None:
    stmt = select(Zone).where(Zone.id == zone_id).where(Zone.is_active.is_(True))
    result = await db.exec(stmt)
    return result.one_or_none()


async def get_registration_for_update(
    db: AsyncSession,
    *,
    participant_id: uuid.UUID,
    zone_id: uuid.UUID,
) -> ZoneRegistration | None:
    stmt = (
        select(ZoneRegistration)
        .where(ZoneRegistration.participant_id == participant_id)
        .where(ZoneRegistration.zone_id == zone_id)
        .with_for_update()
    )
    result = await db.exec(stmt)
    return result.one_or_none()


async def get_registration(
    db: AsyncSession,
    *,
    participant_id: uuid.UUID,
    zone_id: uuid.UUID,
) -> ZoneRegistration | None:
    stmt = (
        select(ZoneRegistration)
        .where(ZoneRegistration.participant_id == participant_id)
        .where(ZoneRegistration.zone_id == zone_id)
    )
    result = await db.exec(stmt)
    return result.one_or_none()


async def create_registration(
    db: AsyncSession,
    *,
    participant_id: uuid.UUID,
    zone_id: uuid.UUID,
    pass_code: str,
) -> ZoneRegistration:
    registration = ZoneRegistration(
        participant_id=participant_id,
        zone_id=zone_id,
        pass_code=pass_code,
        is_active=True,
    )
    db.add(registration)
    await db.flush()
    return registration


async def update_registration(
    db: AsyncSession,
    *,
    registration: ZoneRegistration,
    is_active: bool,
    pass_code: str | None = None,
) -> ZoneRegistration:
    registration.is_active = is_active
    if pass_code is not None:
        registration.pass_code = pass_code
    db.add(registration)
    await db.flush()
    return registration


async def list_active_zone_ids_for_participant(
    db: AsyncSession,
    *,
    participant_id: uuid.UUID,
) -> list[uuid.UUID]:
    stmt = (
        select(ZoneRegistration.zone_id)
        .where(ZoneRegistration.participant_id == participant_id)
        .where(ZoneRegistration.is_active.is_(True))
        .order_by(ZoneRegistration.created_at.asc(), ZoneRegistration.zone_id.asc())
    )
    result = await db.exec(stmt)
    return [row for row in result.all()]


async def list_passes_for_participant(
    db: AsyncSession,
    *,
    participant_id: uuid.UUID,
) -> list[ZoneRegistration]:
    stmt = (
        select(ZoneRegistration)
        .where(ZoneRegistration.participant_id == participant_id)
        .order_by(ZoneRegistration.created_at.asc(), ZoneRegistration.id.asc())
    )
    result = await db.exec(stmt)
    return list(result.all())


async def count_checked_in_zones_for_participant(
    db: AsyncSession,
    *,
    participant_id: uuid.UUID,
) -> int:
    stmt = (
        select(func.count(col(ZoneRegistration.id)))
        .where(ZoneRegistration.participant_id == participant_id)
        .where(ZoneRegistration.is_active.is_(True))
        .where(ZoneRegistration.checked_in_at.is_not(None))
    )
    result = await db.exec(stmt)
    return int(result.one())


async def count_active_zone_registrations_for_participant(
    db: AsyncSession,
    *,
    participant_id: uuid.UUID,
) -> int:
    stmt = (
        select(func.count(col(ZoneRegistration.id)))
        .where(ZoneRegistration.participant_id == participant_id)
        .where(ZoneRegistration.is_active.is_(True))
    )
    result = await db.exec(stmt)
    return int(result.one())


async def list_checked_in_zone_ids_for_participant(
    db: AsyncSession,
    *,
    participant_id: uuid.UUID,
) -> list[uuid.UUID]:
    stmt = (
        select(ZoneRegistration.zone_id)
        .where(ZoneRegistration.participant_id == participant_id)
        .where(ZoneRegistration.is_active.is_(True))
        .where(ZoneRegistration.checked_in_at.is_not(None))
        .order_by(ZoneRegistration.checked_in_at.asc(), ZoneRegistration.zone_id.asc())
    )
    result = await db.exec(stmt)
    return [row for row in result.all()]

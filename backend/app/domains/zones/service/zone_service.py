import secrets
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.auth.models import User
from app.domains.participants.service.profile_lookup_service import get_participant_for_user
from app.domains.zones import crud
from app.domains.zones.models import ZoneRegistration
from app.domains.zones.schemas import (
    MyPassesRead,
    MyRegistrationsRead,
    ZoneCatalogItemRead,
    ZonePassRead,
    ZoneRead,
    ZoneRegistrationRead,
)


def _generate_pass_code() -> str:
    return secrets.token_urlsafe(18)


def _serialize_zone_catalog_item(zone, registered_count: int) -> ZoneCatalogItemRead:
    return ZoneCatalogItemRead(
        id=zone.id,
        name=zone.name,
        shortName=zone.short_name,
        category=zone.category,
        type=zone.zone_type,
        tags=zone.tags or [],
        status=zone.status.value if hasattr(zone.status, "value") else str(zone.status),
        location=zone.location,
        points=zone.points,
        registeredCount=registered_count,
        color=zone.color,
    )


def _serialize_zone_read(zone, registered_count: int) -> ZoneRead:
    row = _serialize_zone_catalog_item(zone, registered_count)
    return ZoneRead(**row.model_dump(), createdAt=zone.created_at, updatedAt=zone.updated_at)


def _serialize_zone_registration(registration: ZoneRegistration) -> ZoneRegistrationRead:
    return ZoneRegistrationRead(
        zoneId=registration.zone_id,
        isActive=registration.is_active,
        code=registration.pass_code,
        checkedInAt=registration.checked_in_at,
    )


def _serialize_zone_pass(registration: ZoneRegistration) -> ZonePassRead:
    return ZonePassRead(
        zoneId=registration.zone_id,
        code=registration.pass_code,
        isActive=registration.is_active,
        checkedInAt=registration.checked_in_at,
    )


async def list_zones(db: AsyncSession) -> list[ZoneCatalogItemRead]:
    rows = await crud.list_active_zones_with_registration_counts(db)
    return [_serialize_zone_catalog_item(zone, registered_count) for zone, registered_count in rows]


async def get_zone_details(db: AsyncSession, *, zone_id: uuid.UUID) -> ZoneRead:
    row = await crud.get_zone_with_registration_count(db, zone_id=zone_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    zone, registered_count = row
    return _serialize_zone_read(zone, registered_count)


async def register_for_zone(
    db: AsyncSession,
    *,
    zone_id: uuid.UUID,
    user: User,
) -> tuple[ZoneRegistrationRead, bool]:
    participant = await get_participant_for_user(db, user=user)
    if participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant profile not found")

    zone = await crud.get_zone_by_id(db, zone_id=zone_id)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    registration = await crud.get_registration_for_update(
        db,
        participant_id=participant.id,
        zone_id=zone_id,
    )
    if registration is not None:
        if registration.is_active:
            return _serialize_zone_registration(registration), False
        updated = await crud.update_registration(
            db,
            registration=registration,
            is_active=True,
            pass_code=_generate_pass_code(),
        )
        return _serialize_zone_registration(updated), False

    for _ in range(5):
        try:
            async with db.begin_nested():
                created = await crud.create_registration(
                    db,
                    participant_id=participant.id,
                    zone_id=zone_id,
                    pass_code=_generate_pass_code(),
                )
            return _serialize_zone_registration(created), True
        except IntegrityError:
            existing = await crud.get_registration(
                db,
                participant_id=participant.id,
                zone_id=zone_id,
            )
            if existing is not None:
                if existing.is_active:
                    return _serialize_zone_registration(existing), False
                updated = await crud.update_registration(
                    db,
                    registration=existing,
                    is_active=True,
                    pass_code=_generate_pass_code(),
                )
                return _serialize_zone_registration(updated), False
            continue

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Could not create zone registration due to pass code collision; retry",
    )


async def unregister_from_zone(
    db: AsyncSession,
    *,
    zone_id: uuid.UUID,
    user: User,
) -> ZoneRegistrationRead:
    participant = await get_participant_for_user(db, user=user)
    if participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant profile not found")

    zone = await crud.get_zone_by_id(db, zone_id=zone_id)
    if zone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    registration = await crud.get_registration_for_update(
        db,
        participant_id=participant.id,
        zone_id=zone_id,
    )
    if registration is None:
        return ZoneRegistrationRead(
            zoneId=zone_id,
            isActive=False,
            code="",
            checkedInAt=None,
        )

    if not registration.is_active:
        return _serialize_zone_registration(registration)

    updated = await crud.update_registration(
        db,
        registration=registration,
        is_active=False,
    )
    return _serialize_zone_registration(updated)


async def list_my_registrations(
    db: AsyncSession,
    *,
    user: User,
) -> MyRegistrationsRead:
    participant = await get_participant_for_user(db, user=user)
    if participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant profile not found")

    zone_ids = await crud.list_active_zone_ids_for_participant(db, participant_id=participant.id)
    return MyRegistrationsRead(zoneIds=zone_ids)


async def list_my_passes(
    db: AsyncSession,
    *,
    user: User,
) -> MyPassesRead:
    participant = await get_participant_for_user(db, user=user)
    if participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant profile not found")

    rows = await crud.list_passes_for_participant(db, participant_id=participant.id)
    return MyPassesRead(passes=[_serialize_zone_pass(row) for row in rows])

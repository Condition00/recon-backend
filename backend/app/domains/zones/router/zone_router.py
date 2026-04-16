import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.database import get_db
from app.domains.auth.models import User
from app.domains.zones import controller
from app.domains.zones.schemas import (
    MyPassesRead,
    MyRegistrationsRead,
    ZoneCatalogItemRead,
    ZoneRead,
    ZoneRegistrationRead,
)
from app.utils.deps import get_current_user

router = APIRouter(tags=["zones"])


@router.get("/zones", response_model=list[ZoneCatalogItemRead])
async def list_zones(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await controller.get_catalog(db)


@router.get("/zones/{zone_id}", response_model=ZoneRead)
async def get_zone(
    zone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await controller.get_one(db, zone_id=zone_id)


@router.post(
    "/zones/{zone_id}/register",
    response_model=ZoneRegistrationRead,
    status_code=status.HTTP_200_OK,
)
async def register_for_zone(
    zone_id: uuid.UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payload, created = await controller.register(db, zone_id=zone_id, user=user)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return payload


@router.delete("/zones/{zone_id}/register", response_model=ZoneRegistrationRead)
async def unregister_from_zone(
    zone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await controller.unregister(db, zone_id=zone_id, user=user)


@router.get("/me/registrations", response_model=MyRegistrationsRead)
async def get_my_registrations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await controller.my_registrations(db, user=user)


@router.get("/me/passes", response_model=MyPassesRead)
async def get_my_passes(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await controller.my_passes(db, user=user)

import uuid

from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.database import get_db
from app.domains.announcements.controller import create, delete, get_active, list_active, update
from app.domains.announcements.schemas import AnnouncementCreate, AnnouncementRead, AnnouncementUpdate
from app.domains.auth.models import ROLE_ADMIN, User
from app.utils.deps import get_current_user, get_redis, require_roles

router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("/", response_model=list[AnnouncementRead])
async def list_announcements_route(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await list_active(db)


@router.get("/{announcement_id}", response_model=AnnouncementRead)
async def get_announcement_route(
    announcement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_active(db, announcement_id)


@router.post("/", response_model=AnnouncementRead, status_code=status.HTTP_201_CREATED)
async def create_announcement_route(
    payload: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(ROLE_ADMIN, "ops")),
    redis: Redis = Depends(get_redis),
):
    return await create(db, payload, admin.id, redis)


@router.patch("/{announcement_id}", response_model=AnnouncementRead)
async def update_announcement_route(
    announcement_id: uuid.UUID,
    payload: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(ROLE_ADMIN, "ops")),
    redis: Redis = Depends(get_redis),
):
    return await update(db, announcement_id, payload, redis)


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement_route(
    announcement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(ROLE_ADMIN, "ops")),
    redis: Redis = Depends(get_redis),
):
    await delete(db, announcement_id, redis)

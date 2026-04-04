import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.domains.auth.controller.user_controller import create_user, delete_user, get_user, list_users, update_user
from app.domains.auth.models import ROLE_ADMIN, User
from app.domains.auth.schemas import UserCreate, UserRead, UserUpdate
from app.utils.deps import get_current_user, require_roles

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user_route(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    return await create_user(payload, db)


@router.get("/", response_model=list[UserRead])
async def list_users_route(skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db),
                            _: User = Depends(require_roles(ROLE_ADMIN))):
    return await list_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserRead)
async def get_user_route(user_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    return await get_user(user_id, current_user, db)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user_route(user_id: uuid.UUID, payload: UserUpdate, db: AsyncSession = Depends(get_db),
                             _: User = Depends(require_roles(ROLE_ADMIN))):
    return await update_user(user_id, payload, db)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_route(user_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                             _: User = Depends(require_roles(ROLE_ADMIN))):
    await delete_user(user_id, db)

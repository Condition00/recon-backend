import datetime
import uuid

from pydantic import EmailStr
from sqlmodel import SQLModel

from app.domains.auth.models import UserBase


class RoleRead(SQLModel):
    id: uuid.UUID
    name: str
    description: str | None = None


class UserCreate(SQLModel):
    email: EmailStr
    username: str
    password: str


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime.datetime
    role: RoleRead | None = None


class UserProfile(UserBase):
    id: uuid.UUID
    created_at: datetime.datetime
    role: RoleRead | None = None


class UserUpdate(SQLModel):
    email: EmailStr | None = None
    username: str | None = None
    password: str | None = None
    is_active: bool | None = None
    role_name: str | None = None

import datetime
import uuid
from typing import Any

from pydantic import EmailStr, Field
from sqlmodel import SQLModel

from app.models.user import UserBase


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
    form_response: dict[str, Any] | None = None
    role: RoleRead | None = None


class ApplicationSubmit(SQLModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone_number: str = Field(min_length=7, max_length=20)
    dob: datetime.date
    resume_file_key: str = Field(min_length=1, max_length=512)


class UserUpdate(SQLModel):
    email: EmailStr | None = None
    username: str | None = None
    password: str | None = None
    is_active: bool | None = None
    status: str | None = None
    role_name: str | None = None

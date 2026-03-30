import uuid
from typing import Any, Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import Base

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"


class UserBase(SQLModel):
    email: str = Field(max_length=320, unique=True, index=True)
    username: str = Field(max_length=50, unique=True, index=True)
    is_active: bool = Field(default=True)
    status: Optional[str] = Field(
        default=None,
        max_length=50,
        nullable=True,
    )

class User(Base, UserBase, table=True):
    __tablename__ = "users"

    hashed_password: Optional[str] = Field(default=None, max_length=128)
    form_response: Optional[dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    role_id: uuid.UUID | None = Field(default=None, foreign_key="roles.id", index=True)

    # Relationships
    role: Optional["Role"] = Relationship(back_populates="users")
    oauth_accounts: list["OAuthAccount"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    refresh_tokens: list["RefreshToken"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


# Avoid circular imports — these are imported for type resolution only
from app.models.role import Role  # noqa: E402, F401
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.refresh_token import RefreshToken  # noqa: E402, F401

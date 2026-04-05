import uuid
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.utils.models.base import Base


class UserBase(SQLModel):
    email: str = Field(max_length=320, unique=True, index=True)
    username: str = Field(max_length=50, unique=True, index=True)
    is_active: bool = Field(default=True)


class User(Base, UserBase, table=True):
    __tablename__ = "users"

    hashed_password: Optional[str] = Field(default=None, max_length=128)
    role_id: uuid.UUID | None = Field(default=None, foreign_key="roles.id", index=True)

    role: Optional["Role"] = Relationship(
        back_populates="users",
    )
    oauth_accounts: list["OAuthAccount"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    refresh_tokens: list["RefreshToken"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    participant: Optional["Participant"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False, "foreign_keys": "Participant.user_id"},
    )


from app.domains.auth.models.role import Role  # noqa: E402, F401
from app.domains.auth.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.domains.auth.models.refresh_token import RefreshToken  # noqa: E402, F401
from app.domains.participants.models.participant import Participant  # noqa: E402, F401

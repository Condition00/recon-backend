import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

from app.utils.models.base import Base


class RefreshTokenBase(SQLModel):
    token_hash: str = Field(max_length=64, unique=True, index=True)
    expires_at: datetime.datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    is_revoked: bool = Field(default=False)


class RefreshToken(Base, RefreshTokenBase, table=True):
    __tablename__ = "refresh_tokens"

    user_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    )

    user: "User" = Relationship(back_populates="refresh_tokens")


from app.domains.auth.models.user import User  # noqa: E402, F401

import uuid

from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.utils.models.base import Base


class OAuthAccountBase(SQLModel):
    provider: str = Field(max_length=50)
    provider_user_id: str = Field(max_length=255)
    provider_email: str = Field(max_length=320)


class OAuthAccount(Base, OAuthAccountBase, table=True):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
    )

    user_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    )

    user: "User" = Relationship(back_populates="oauth_accounts")


from app.domains.auth.models.user import User  # noqa: E402, F401

import uuid

from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import Base


class OAuthAccountBase(SQLModel):
    provider: str = Field(max_length=50)  # "google", "github", etc.
    provider_user_id: str = Field(max_length=255)  # sub / id from provider
    provider_email: str = Field(max_length=320)


class OAuthAccount(Base, OAuthAccountBase, table=True):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
    )

    user_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    )

    # Relationships
    user: "User" = Relationship(back_populates="oauth_accounts")


from app.models.user import User  # noqa: E402, F401

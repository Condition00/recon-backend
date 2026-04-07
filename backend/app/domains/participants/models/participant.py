import uuid
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

from app.utils.models.base import Base


class ParticipantBase(SQLModel):
    display_name: str = Field(max_length=50, unique=True, index=True)
    institution: str = Field(max_length=100)
    year: int = Field(ge=1, le=5)
    linkedin_acc: str | None = Field(default=None, max_length=300)
    github_acc: str | None = Field(default=None, max_length=300)
    x_acc: str | None = Field(default=None, max_length=300)
    phone: str | None = Field(default=None, max_length=20)
    profile_photo_file_key: str | None = Field(default=None, max_length=500)


class Participant(Base, ParticipantBase, table=True):
    __tablename__ = "participants"

    talent_visible: bool = Field(default=False)
    talent_contact_shareable: bool = Field(default=False)
    checked_in_at: datetime | None = Field(default=None)
    checked_in_by: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    user_id: uuid.UUID = Field(foreign_key="users.id", unique=True, index=True)

    user: "User" = Relationship(
        back_populates="participant",
        sa_relationship_kwargs={"foreign_keys": "Participant.user_id"},
    )


from app.domains.auth.models.user import User  # noqa: E402, F401
